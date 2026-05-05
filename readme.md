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

## GitHub Actions self-hosted runner

### add helm repository

```
helm repo add actions-runner-controller https://actions-runner-controller.github.io/actions-runner-controller
```

### install actions-runner-controller

Replace `<GITHUB_TOKEN>` with a GitHub personal access token that has access to the repository.

```
helm upgrade --install actions-runner-controller actions-runner-controller/actions-runner-controller \
  --namespace actions-runner-system \
  --create-namespace \
  --set=authSecret.create=true \
  --set=authSecret.github_token="<GITHUB_TOKEN>" \
  --wait
```

### create runner deployment

```
cat << EOF | kubectl apply -n actions-runner-system -f -
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: self-hosted-runner
spec:
  replicas: 1
  template:
    spec:
      repository: donascimentomarcelo/python-app-backstage
EOF
```

## Access Argo CD with `argocd-server.argocd`

This section documents the steps used to make this command work from the local machine:

```
curl -k https://argocd-server.argocd
```

### what was the problem

The Kubernetes service already existed:

```
argocd-server
```

And it was running in this namespace:

```
argocd
```

Inside the Kubernetes cluster, a service can be reached by DNS using names like:

```
argocd-server.argocd
argocd-server.argocd.svc.cluster.local
```

However, this DNS name only works inside Kubernetes. When running `curl` from Windows, the local machine does not know how to resolve `argocd-server.argocd`.

So this command failed:

```
curl https://argocd-server.argocd
```

With an error like:

```
curl: (6) Could not resolve host: argocd-server.argocd
```

Another important detail is that the service was type `ClusterIP`:

```
kubectl get svc -n argocd
```

Example:

```
NAME            TYPE        CLUSTER-IP      PORT(S)
argocd-server   ClusterIP   10.98.134.151   80/TCP,443/TCP
```

`ClusterIP` services are only reachable from inside the cluster. To access Argo CD from the local machine, it needs to be exposed through something like an Ingress, a NodePort, a LoadBalancer, or a port-forward.

In this setup, the chosen solution was to use the existing nginx Ingress.

### expose Argo CD through Ingress

First, check the current Ingress:

```
kubectl get ingress argocd-server -n argocd -o yaml
```

The Ingress was already pointing to the correct service, but it was using another host:

```
argocd.test.local
```

It was changed to use:

```
argocd-server.argocd
```

The final Ingress should look like this:

```
kubectl get ingress argocd-server -n argocd -o wide
```

Expected result:

```
NAME            CLASS   HOSTS                  ADDRESS     PORTS
argocd-server   nginx   argocd-server.argocd   localhost   80, 443
```

The important parts are:

```
HOSTS:   argocd-server.argocd
ADDRESS: localhost
PORTS:   80, 443
```

This means that the nginx Ingress controller is listening locally and will route requests for `argocd-server.argocd` to the `argocd-server` service.

### add local DNS entry on Windows

Because `argocd-server.argocd` is not a real public DNS name, Windows needs a local hosts entry.

Open PowerShell as Administrator and add this line to the hosts file:

```
Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "127.0.0.1 argocd-server.argocd"
```

This tells Windows:

```
argocd-server.argocd -> 127.0.0.1
```

So when this command is executed:

```
curl https://argocd-server.argocd
```

The request goes to `localhost`, where the nginx Ingress is exposed.

You can verify the local DNS entry with:

```
Resolve-DnsName argocd-server.argocd
```

Expected result:

```
Name                  Type   IPAddress
argocd-server.argocd  A      127.0.0.1
```

You can also verify that port `443` is reachable:

```
Test-NetConnection argocd-server.argocd -Port 443
```

Expected result:

```
TcpTestSucceeded : True
```

### configure the TLS secret used by Ingress

The Ingress was configured to use this TLS secret:

```
argocd-server-tls
```

Check the Ingress:

```
kubectl describe ingress argocd-server -n argocd
```

Expected TLS section:

```
TLS:
  argocd-server-tls terminates argocd-server.argocd
```

If the secret does not exist, check it with:

```
kubectl get secret argocd-server-tls -n argocd
```

If it returns `NotFound`, create the secret using the certificate that already exists in `argocd-secret`:

```
$src = kubectl get secret argocd-secret -n argocd -o json | ConvertFrom-Json

$obj = [ordered]@{
  apiVersion = "v1"
  kind = "Secret"
  metadata = @{
    name = "argocd-server-tls"
    namespace = "argocd"
  }
  type = "kubernetes.io/tls"
  data = @{
    "tls.crt" = $src.data."tls.crt"
    "tls.key" = $src.data."tls.key"
  }
}

$obj | ConvertTo-Json -Depth 6 | kubectl apply -f -
```

Expected result:

```
secret/argocd-server-tls created
```

### test the final access

Now run:

```
curl https://argocd-server.argocd
```

Because the certificate is local/self-signed, the expected result is a certificate validation error:

```
curl: (60) SSL certificate problem: unable to get local issuer certificate
```

Then run with `-k`:

```
curl -k https://argocd-server.argocd
```

Expected result:

```
<!doctype html><html lang="en"><head><meta charset="UTF-8"><title>Argo CD</title>...
```

The `-k` option means "skip TLS certificate validation". It does not select a namespace and it does not fix DNS.

In short:

```
curl
  -> argocd-server.argocd
  -> 127.0.0.1
  -> nginx ingress
  -> service argocd-server in namespace argocd
  -> Argo CD server pod
```
