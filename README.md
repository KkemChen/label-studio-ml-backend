```bash
#!/bin/sh

# 使用Dockerfile构建ml_backend完整镜像
# docker build -t label_studio_ml_backend .

# 拉取最新的本体镜像
# docker pull heartexlabs/label-studio:latest

# cd dist/label-studio
# 可修改docker-compose.yml中相应配置，如端口
# docker-compose up

# cd dist/label-studio-ml-backend
# 登录配置好的本体，获取token，然后配置到该docker-compose.yml中，此处模型为yolo模型，自行参考进行配置
# docker-compose up
```

-----------------------------------------------------

```bash
# 打包为本地文件
#   - docker save -o label_studio_ml_backend.tar label_studio_ml_backend
#   - docker save -o label_studio_v1.13.1.tar heartexlabs/label-studio:latest

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

