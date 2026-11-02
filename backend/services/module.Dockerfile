# Builds any module service. Context is backend/; pick one with --build-arg SERVICE=ptx_service.
FROM python:3.14-slim
ARG SERVICE
WORKDIR /srv
COPY libs/urban_common /srv/libs/urban_common
RUN pip install --no-cache-dir /srv/libs/urban_common
COPY services/${SERVICE}/app /srv/app
RUN useradd --create-home --uid 10001 appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
