# How to install locally

### install dependencies

```
python -m pip install -r requirements.txt
```

### run the app

```
python src/app.py
```

### build docker image

```
docker build -t python-app:latest .
```

### run docker container

```
docker run -p 8080:5000 python-app:latest
```

### test endpoint

```
curl --location "http://127.0.0.1:8080/api/v1/details"
```
