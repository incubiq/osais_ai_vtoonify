
source: https://github.com/williamyang1991/VToonify

// build conda env with ai_vtoonify.conda.yml
// runs locally with ai_vtoonify
conda activate ai_vtoonify


// manual test without OSAIS
1/ go in /ai
2/ python style_transfer.py --content ../_input/warmup.jpeg --scale_image --backbone toonify --ckpt ./checkpoint/vtoonify_t_comic/vtoonify.pt --padding 400 400 400 400 --output_path ../_output   

// how to run it locally -> WITH FLASK (compat old libs)
$env:FLASK_APP="../osais_ai_base/main_flask"
python -m flask run --host=0.0.0.0 --port=5308

// how to run it locally (preferred)
uvicorn main:app --host 0.0.0.0 --port 5308

// how to build it 
docker build -t yeepeekoo/public:ai_vtoonify_ .  
docker build -t yeepeekoo/public:ai_vtoonify .  
docker push yeepeekoo/public:ai_vtoonify

// how to run it alongside a local GATEWAY
docker run -d --name ai_vtoonify --gpus all --publish 5308:5308 --env-file env_docker_local yeepeekoo/public:ai_vtoonify

// how to run as VAI locally
1/ copy content of env_vai into env_local
2/ uvicorn main:app --host 0.0.0.0 --port 5308

// how to run it locally as a VAI in docker  (change REF to OSAIS in env file if needed)
docker run -d --name ai_vtoonify --gpus all --expose 5308 --publish 5308:5308 --env-file env_docker_local_vai yeepeekoo/public:ai_vtoonify
