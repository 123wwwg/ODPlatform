# ODPlatform Web

基于 Django 5、Django REST Framework 和 Vue 3 的缺陷检测台账系统。

## 功能

- 缺陷记录新增、查看、编辑和删除
- 原始图片与缺陷标注图上传、预览
- 缺陷类型筛选、关键字搜索
- 总记录数、今日记录数、高置信度数量和平均置信度统计
- 自动展示最新训练任务、mAP、Precision、Recall、类别指标和训练曲线
- Django 模板页面与后台管理
- 本地 Vue 3.5.44、Axios 1.20.0，无需 Node 或 CDN

## 启动

```powershell
conda activate ODP
cd C:\Users\DELL\ODPlatform
powershell -ExecutionPolicy Bypass -File .\scripts\run_web.ps1
```

访问：

- Vue 工作台：<http://127.0.0.1:8000/>
- Django 模板列表：<http://127.0.0.1:8000/defect/list/>
- 后台管理：<http://127.0.0.1:8000/admin/>
- DRF 接口：<http://127.0.0.1:8000/api/>

首次使用后台管理前可创建管理员：

```powershell
cd apps\web-backend
python manage.py createsuperuser
```

## 代码位置

```text
apps/web-backend/
├── manage.py                         Django 命令入口
├── config/
│   ├── settings.py                   数据库、静态文件、CORS、DRF 配置
│   ├── urls.py                       API、后台、模板页面和首页路由
│   └── views.py                      返回 Vue 首页
├── defect/
│   ├── models.py                     DefectType、DefectRecord 数据模型
│   ├── serializers.py                DRF 序列化器
│   ├── api_views.py                  缺陷 CRUD 与统计 API
│   ├── views.py                      Django FBV 页面视图
│   ├── forms.py                      图片上传表单
│   ├── admin.py                      Django 后台配置
│   ├── migrations/                   数据库迁移及默认缺陷类型
│   └── templates/defect/             Django 模板页面
└── frontend/
    ├── index.html                    Vue 工作台页面结构
    └── static/frontend/
        ├── styles.css                页面样式
        ├── app.js                    Vue 交互与 Axios API 调用
        └── vendor/                   本地 Vue 与 Axios
```

数据库为 `apps/web-backend/db.sqlite3`，上传图片保存在
`apps/web-backend/media/`。

## API

| 方法 | 地址 | 用途 |
|---|---|---|
| GET | `/api/defect-record/` | 查询记录 |
| POST | `/api/defect-record/` | 新增记录，使用 multipart/form-data |
| GET/PATCH/DELETE | `/api/defect-record/{id}/` | 查询、修改、删除单条记录 |
| GET | `/api/defect-type/` | 查询缺陷类型 |
| GET | `/api/stats/` | 查询统计概览 |
| GET | `/api/model/` | 查询最新模型训练结果 |
| GET | `/api/model/training-curve/` | 获取训练曲线图片 |

## Rubbish 数据集训练

```powershell
cd C:\Users\DELL\ODPlatform
conda activate ODP
powershell -ExecutionPolicy Bypass -File .\scripts\train_rubbish.ps1
```

默认执行 1 epoch、416 图像尺寸的 CPU 演示训练。正式训练示例：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\train_rubbish.ps1 `
  -Epochs 50 -ImageSize 640 -Batch 16 -Device 0
```

训练完成后刷新 Web 页面，“模型训练”区域会自动读取最新运行现场。

当前仓库中的模型是 CPU 上 1 个 epoch 的演示训练结果，只用于验证完整链路，
不应作为最终精度模型。正式训练建议使用 GPU，并把 `Epochs` 提高到 50–100。
原数据的类别名为 `class_0` 到 `class_9`；如果已有真实垃圾类别名称，应在
`odp-transform` 的 `--classes` 参数和重新生成的 YAML 中使用真实名称。

当前为本地开发演示配置，API 未启用登录鉴权，且 CORS 在 `DEBUG=1` 时允许
所有来源。部署到生产环境前必须关闭 `DEBUG`、配置鉴权、限制 CORS，并使用
正式 WSGI/ASGI 服务。
