
##
##      VTOONIFY AI
##

## ------------------------------------------------------------------------
#       Generic (All AIs)
## ------------------------------------------------------------------------

import os, sys, argparse, shutil, time
from datetime import datetime

## for calling back OSAIS from AI
gNotifyCallback=None
gNotifyParams=None

## Notifications from AI
def setNotifyCallback(cb, _aParams): 
    global gNotifyParams
    global gNotifyCallback

    gNotifyParams=_aParams
    gNotifyCallback=cb

## For a debug breakpoint
def fnDebug(): 
    return True

## where to save the user profile?
def fnGetUserdataPath(_username):
    _path=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DEFAULT_PROFILE_DIR = os.path.join(_path, '_profile')
    USER_PROFILE_DIR = os.path.join(DEFAULT_PROFILE_DIR, _username)
    return {
        "location": USER_PROFILE_DIR,
        "voice": False,
        "picture": True
    }

## ------------------------------------------------------------------------
#       Specific
## ------------------------------------------------------------------------

from pathlib import Path

## init
sys.path.insert(0, './ai')

#os.environ['CUDA_VISIBLE_DEVICES'] = "0"
import numpy as np
import cv2
import dlib
import torch
from torchvision import transforms
import torch.nn.functional as F
from tqdm import tqdm
from model.vtoonify import VToonify
from model.bisenet.model import BiSeNet
from model.encoder.align_all_parallel import align_face
from util import save_image, load_image, visualize, load_psp_standalone, get_video_crop_parameter, tensor2cv2

## WARMUP Data
def getWarmupData(_id):
    try:
        import time
        from werkzeug.datastructures import MultiDict
        ts=int(time.time())
        sample_args = MultiDict([
            ('-u', 'test_user'),
            ('-uid', str(ts)),
            ('-t', _id),
            ('-cycle', '0'),
            ('--scale_image', "True"),
            ('--video', "False"),
            ('--ckpt', "vtoonify_t_pixar/vtoonify.pt"),
            ('--backbone', "toonify"),
            ('-o', 'warmup.jpg'),
            ('-filename', 'warmup.jpg')
        ])
        return sample_args
    except Exception as err:
        print("Could not call warm up!\r\n")
        return None

## RUN AI
def fnRun(_args): 
    # Create the parser
    vq_parser = argparse.ArgumentParser(description='VToonify')

    # OSAIS arguments
    vq_parser.add_argument("-odir", "--outdir", type=str, help="Output directory", default="./_output/", dest='outdir')
    vq_parser.add_argument("-idir", "--indir", type=str, help="input directory", default="./_input/", dest='indir')

    # Add the arguments
    vq_parser.add_argument("-filename", "--filename", type=str, default='./warmup.jpeg', help="path of the content image/video", dest='input_file')
    vq_parser.add_argument("--style_id", type=int, default=26, help="the id of the style image")
    vq_parser.add_argument("--style_degree", type=float, default=0.5, help="style degree for VToonify-D")
    vq_parser.add_argument("--color_transfer", action="store_true", help="transfer the color of the style")
    vq_parser.add_argument("--ckpt", type=str, default='vtoonify_d_cartoon/vtoonify_s_d.pt', help="path of the saved model")
    vq_parser.add_argument("--scale_image", type=str, help="resize and crop the image to best fit the model")
    vq_parser.add_argument("--style_encoder_path", type=str, default='encoder.pt', help="path of the style encoder")
    vq_parser.add_argument("--exstyle_path", type=str, default=None, help="path of the extrinsic style code")
    vq_parser.add_argument("--faceparsing_path", type=str, default='faceparsing.pth', help="path of the face parsing model")
    vq_parser.add_argument("--video",  type=str, help="if true, video stylization; if false, image stylization")
    vq_parser.add_argument("--cpu", action="store_true", help="if true, only use cpu")
    vq_parser.add_argument("--backbone", type=str, default='dualstylegan', help="dualstylegan | toonify")
    vq_parser.add_argument("--padding", type=int, default=200, help="left, right, top, bottom paddings to the face center")
    vq_parser.add_argument("--batch_size", type=int, default=4, help="batch size of frames when processing video")
    vq_parser.add_argument("--parsing_map_path", type=str, default=None, help="path of the refined parsing map of the target video")
    vq_parser.add_argument("-o", "--output", type=str, nargs="?", help="filename to write results to", default="result.jpg", dest="output_file")


    # Execute the parse_args() method
    try:
        args = vq_parser.parse_args(_args)
        print(args)

        if args.exstyle_path is None:
            args.exstyle_path = os.path.join("./ai/checkpoint/", os.path.dirname(args.ckpt), 'exstyle_code.npy')

        # uncomment to see log of all params
        # print('Load options')
        # _tmpArg=vars(args)      
        # for name, value in sorted(_tmpArg.items()):
        #    print('%s: %s' % (str(name), str(value)))

        beg_date = datetime.utcnow()

        ## start toonify HERE
        device = "cpu" if args.cpu else "cuda"       
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5],std=[0.5,0.5,0.5]),
            ])
        
        vtoonify = VToonify(backbone = args.backbone)
        _ckpt=os.path.join(Path.cwd(), "ai/checkpoint/", args.ckpt)
        vtoonify.load_state_dict(torch.load(_ckpt, map_location=lambda storage, loc: storage)['g_ema'])
        vtoonify.to(device)

        parsingpredictor = BiSeNet(n_classes=19)
        _fp=os.path.join(Path.cwd(), "ai/checkpoint/", args.faceparsing_path)
        parsingpredictor.load_state_dict(torch.load(_fp, map_location=lambda storage, loc: storage))
        parsingpredictor.to(device).eval()

        modelname = './ai/checkpoint/shape_predictor_68_face_landmarks.dat'
        if not os.path.exists(modelname):
            import wget, bz2
            wget.download('http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2', modelname+'.bz2')
            zipfile = bz2.BZ2File(modelname+'.bz2')
            data = zipfile.read()
            open(modelname, 'wb').write(data) 
        landmarkpredictor = dlib.shape_predictor(modelname)

        _sep=os.path.join(Path.cwd(), "ai/checkpoint/", args.style_encoder_path)
        pspencoder = load_psp_standalone(_sep, device)    

        if args.backbone == 'dualstylegan':
            exstyles = np.load(args.exstyle_path, allow_pickle='TRUE').item()
            stylename = list(exstyles.keys())[args.style_id]
            exstyle = torch.tensor(exstyles[stylename]).to(device)
            with torch.no_grad():  
                exstyle = vtoonify.zplus2wplus(exstyle)

        if (args.video=="true" or args.video=="True") and args.parsing_map_path is not None:
            x_p_hat = torch.tensor(np.load(args.parsing_map_path))          
                
        print('Load models successfully!')
        
        
        filename = os.path.join(args.indir, args.input_file)
        basename = os.path.basename(filename).split('.')[0]
        savename = os.path.join(args.outdir, args.output_file)

        scale = 1
        kernel_1d = np.array([[0.125],[0.375],[0.375],[0.125]])
        print('Processing ' + os.path.basename(filename) + ' with vtoonify_' + args.backbone[0])
        if (args.video=="true" or args.video=="True"):
            cropname = os.path.join(args.outdir, basename + '_input.mp4')
            # savename = os.path.join(args.outdir, basename + '_vtoonify_' +  args.backbone[0] + '.mp4')

            video_cap = cv2.VideoCapture(filename)
            num = int(video_cap.get(7))

            first_valid_frame = True
            batch_frames = []
            for i in tqdm(range(num)):
                success, frame = video_cap.read()
                if success == False:
                    assert('load video frames error')
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # We proprocess the video by detecting the face in the first frame, 
                # and resizing the frame so that the eye distance is 64 pixels.
                # Centered on the eyes, we crop the first frame to almost 400x400 (based on args.padding).
                # All other frames use the same resizing and cropping parameters as the first frame.
                if first_valid_frame:
                    if args.scale_image=="true" or args.scale_image=="True":
                        paras = get_video_crop_parameter(frame, landmarkpredictor, [args.padding, args.padding, args.padding, args.padding])
                        if paras is None:
                            continue
                        h,w,top,bottom,left,right,scale = paras
                        H, W = int(bottom-top), int(right-left)
                        # for HR video, we apply gaussian blur to the frames to avoid flickers caused by bilinear downsampling
                        # this can also prevent over-sharp stylization results. 
                        if scale <= 0.75:
                            frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d)
                        if scale <= 0.375:
                            frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d)
                        frame = cv2.resize(frame, (w, h))[top:bottom, left:right]
                    else:
                        H, W = frame.shape[0], frame.shape[1]

                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    videoWriter = cv2.VideoWriter(cropname, fourcc, video_cap.get(5), (W, H))
                    videoWriter2 = cv2.VideoWriter(savename, fourcc, video_cap.get(5), (4*W, 4*H))
                    
                    # For each video, we detect and align the face in the first frame for pSp to obtain the style code. 
                    # This style code is used for all other frames.
                    with torch.no_grad():
                        I = align_face(frame, landmarkpredictor)
                        I = transform(I).unsqueeze(dim=0).to(device)
                        s_w = pspencoder(I)
                        s_w = vtoonify.zplus2wplus(s_w)
                        if vtoonify.backbone == 'dualstylegan':
                            if args.color_transfer:
                                s_w = exstyle
                            else:
                                s_w[:,:7] = exstyle[:,:7]
                    first_valid_frame = False
                elif args.scale_image=="true" or args.scale_image=="True":
                    if scale <= 0.75:
                        frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d)
                    if scale <= 0.375:
                        frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d)
                    frame = cv2.resize(frame, (w, h))[top:bottom, left:right]

                # videoWriter.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

                batch_frames += [transform(frame).unsqueeze(dim=0).to(device)]

                if len(batch_frames) == args.batch_size or (i+1) == num:
                    x = torch.cat(batch_frames, dim=0)
                    batch_frames = []
                    with torch.no_grad():
                        # parsing network works best on 512x512 images, so we predict parsing maps on upsmapled frames
                        # followed by downsampling the parsing maps
                        if (args.video=="true" or args.video=="True") and args.parsing_map_path is not None:
                            x_p = x_p_hat[i+1-x.size(0):i+1].to(device)
                        else:
                            x_p = F.interpolate(parsingpredictor(2*(F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)))[0], 
                                            scale_factor=0.5, recompute_scale_factor=False).detach()
                        # we give parsing maps lower weight (1/16)
                        inputs = torch.cat((x, x_p/16.), dim=1)
                        # d_s has no effect when backbone is toonify
                        y_tilde = vtoonify(inputs, s_w.repeat(inputs.size(0), 1, 1), d_s = args.style_degree)       
                        y_tilde = torch.clamp(y_tilde, -1, 1)
                    for k in range(y_tilde.size(0)):
                        videoWriter2.write(tensor2cv2(y_tilde[k].cpu()))

            videoWriter.release()
            videoWriter2.release()
            video_cap.release()

        
        else:
            cropname = os.path.join(args.outdir, basename + '_input.jpg')
            # savename = os.path.join(args.outdir, basename + '_vtoonify_' +  args.backbone[0] + '.jpg')

            frame = cv2.imread(filename)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # We detect the face in the image, and resize the image so that the eye distance is 64 pixels.
            # Centered on the eyes, we crop the image to almost 400x400 (based on args.padding).
            if args.scale_image:
                paras = get_video_crop_parameter(frame, landmarkpredictor, [args.padding, args.padding, args.padding, args.padding])
                if paras is not None:
                    h,w,top,bottom,left,right,scale = paras
                    H, W = int(bottom-top), int(right-left)
                    # for HR image, we apply gaussian blur to it to avoid over-sharp stylization results
                    if scale <= 0.75:
                        frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d)
                    if scale <= 0.375:
                        frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d)
                    frame = cv2.resize(frame, (w, h))[top:bottom, left:right]

            with torch.no_grad():
                I = align_face(frame, landmarkpredictor)
                I = transform(I).unsqueeze(dim=0).to(device)
                s_w = pspencoder(I)
                s_w = vtoonify.zplus2wplus(s_w)
                if vtoonify.backbone == 'dualstylegan':
                    if args.color_transfer:
                        s_w = exstyle
                    else:
                        s_w[:,:7] = exstyle[:,:7]

                x = transform(frame).unsqueeze(dim=0).to(device)
                # parsing network works best on 512x512 images, so we predict parsing maps on upsmapled frames
                # followed by downsampling the parsing maps
                x_p = F.interpolate(parsingpredictor(2*(F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)))[0], 
                                    scale_factor=0.5, recompute_scale_factor=False).detach()
                # we give parsing maps lower weight (1/16)
                inputs = torch.cat((x, x_p/16.), dim=1)
                # d_s has no effect when backbone is toonify
                y_tilde = vtoonify(inputs, s_w.repeat(inputs.size(0), 1, 1), d_s = args.style_degree)        
                y_tilde = torch.clamp(y_tilde, -1, 1)

            # cv2.imwrite(cropname, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            save_image(y_tilde[0].cpu(), savename)
            
        
        ## return output
        end_date = datetime.utcnow()
        return {
            "beg_date": beg_date,
            "end_date": end_date,
            "aFile": [savename]
        }

    except Exception as err:
        print("\r\nCRITICAL ERROR!!!")
        raise err


