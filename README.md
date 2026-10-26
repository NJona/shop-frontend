# shop-frontend

Demo app for Codesphere global deployments. Its landscape (`ci.prod.yml`) has a public `web` page and a private
`api-gateway`. The global config places it on the cheapest DC and lets `api-gateway` call the backend app's
`inference` service in the GPU DC; `BACKEND_URL` is set by the global deployment, not by this repo.
