##
##      To build the AI_VTOONIFY docker image
##

# base stuff
FROM yeepeekoo/public:ai_vtoonify_

## keep ai in its directory
RUN mkdir -p ./ai
RUN chown -R root:root ./ai
COPY ./ai/checkpoint/shape_predictor_68_face_landmarks.dat ./ai/checkpoint/shape_predictor_68_face_landmarks.dat
COPY ./ai/checkpoint/faceparsing.pth ./ai/checkpoint/faceparsing.pth
COPY ./ai/checkpoint/encoder.pt ./ai/checkpoint/encoder.pt
COPY ./ai/checkpoint/directions.npy ./ai/checkpoint/directions.npy
COPY ./ai/checkpoint/exstyle_code.npy ./ai/checkpoint/exstyle_code.npy
COPY ./ai/checkpoint/vtoonify_t_pixar ./ai/checkpoint/vtoonify_t_pixar
COPY ./ai/checkpoint/vtoonify_t_comic ./ai/checkpoint/vtoonify_t_comic
COPY ./ai/checkpoint/vtoonify_t_cartoon ./ai/checkpoint/vtoonify_t_cartoon
COPY ./ai/checkpoint/vtoonify_t_caricature ./ai/checkpoint/vtoonify_t_caricature
COPY ./ai/checkpoint/vtoonify_t_arcane ./ai/checkpoint/vtoonify_t_arcane
COPY ./ai/model ./ai/model
COPY ./ai/util.py ./ai/util.py
COPY ./ai/runai.py ./ai/runai.py

# push again the base files
COPY ./_temp/static/* ./static
COPY ./_temp/templates/* ./templates
COPY ./_temp/osais.json .
COPY ./_temp/main_fastapi.py .
COPY ./_temp/main_flask.py .
COPY ./_temp/main_common.py .

COPY ./_temp/osais_auth.py .
COPY ./_temp/osais_config.py .
COPY ./_temp/osais_inference.py .
COPY ./_temp/osais_main.py .
COPY ./_temp/osais_pricing.py .
COPY ./_temp/osais_s3.py .
COPY ./_temp/osais_training.py .
COPY ./_temp/osais_utils.py .

# copy OSAIS mapping into AI
COPY ./_input/warmup.jpg ./_input/warmup.jpg
COPY ./vtoonify.json .

# overload config with those default settings
ENV ENGINE=vtoonify

# run as a server
CMD ["uvicorn", "main_fastapi:app", "--host", "0.0.0.0", "--port", "5308"]
