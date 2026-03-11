# 任务拆解目录

> 这里放任务拆分、工作包、执行编排和协作材料。

## 当前约定

- 新增任务拆解优先进入 `workdocs/任务拆解/`
- 历史任务拆解仍可能暂时保留在 `docs/内部参考/任务拆解/`
- 自动执行运行态和锁文件不应长期继续留在文档主区

## 运行态约定

- 新的任务级运行态 canonical 路径：`.artifacts/states/task_splits/<task_split_dir>/`
- 旧的 `docs/内部参考/任务拆解/<task_split_dir>/.state/` 只保留迁移期兼容软链接
