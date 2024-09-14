```bash
#!/bin/sh

# 使用Dockerfile构建ml_backend完整镜像
# docker build -t label_studio_ml_backend .

# 拉取最新的本体镜像
# docker pull heartexlabs/label-studio:latest

# docker save -o label_studio_ml_backend.tar label_studio_ml_backend
# docker save -o label_studio_v1.13.1.tar heartexlabs/label-studio:latest

# dist
# ├── label-studio
# │   ├── docker-compose.yml
# │   ├── label_studio_v1.13.1.tar
# │   ├── localstorage
# │   └── mydata
# └── label-studio-ml-backend
#     ├── docker-compose.yml
#     ├── label_studio_ml_backend.tar
#     ├── model.py
#     └── models
#         └── best.pt
```