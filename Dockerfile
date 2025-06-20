FROM python:3.12.8

ARG P_CURRENT_ACTIVE
ARG P_CURRENT_PORT

# RUN if [ "$P_CURRENT_ACTIVE" = "dev" ]; then \
#       echo "FASTAPI_ROOT_PATH=/edaapi-$P_CURRENT_ACTIVE" >> /etc/environment; \
#     elif [ "$P_CURRENT_ACTIVE" = "stg" ]; then \
#       echo "FASTAPI_ROOT_PATH=/edaapi" >> /etc/environment; \
#     else \
#       echo "FASTAPI_ROOT_PATH=/edaapi" >> /etc/environment; \
#     fi

# ENV FASTAPI_ROOT_PATH="/edaapi-"${P_CURRENT_ACTIVE}

# ENV PORT=${P_CURRENT_PORT}
ENV PORT=8000

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", ${ACTIVE}]
# CMD uvicorn main:app --host 0.0.0.0 --port $PORT
#CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
RUN echo '#!/bin/bash\nsource /etc/environment\nexport $(cat /etc/environment | xargs)\nuvicorn main:app --host 0.0.0.0 --port $PORT' > /code/start.sh
RUN chmod +x /code/start.sh

CMD ["/code/start.sh"]