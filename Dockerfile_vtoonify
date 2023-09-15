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
COPY ./_temp/osais_debug.py .

# copy OSAIS mapping into AI
COPY ./vtoonify.json .

# overload config with those default settings
ENV ENGINE=vtoonify

# run as a server
CMD ["uvicorn", "main_fastapi:app", "--host", "0.0.0.0", "--port", "5308"]
