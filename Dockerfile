FROM python:3.12.8

ARG P_CURRENT_ACTIVE
ARG P_CURRENT_PORT

ENV PORT=${P_CURRENT_PORT}

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