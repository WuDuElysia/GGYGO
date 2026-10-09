---
inclusion: fileMatch
fileMatchPattern: ["Source/**/*.h", "Source/**/*.cpp"]
---

# 代码注释

中文注释解释当前契约、理由和非显然约束：状态归属、调用／线程时机、单位／坐标系、网络预测及必要保护。不要复述代码或把 Git 变更历史、任务阶段、已删除类清单写入源码。

未实现功能写当前事实及可见后果，不写计划时间线。可以引用仍存在的 Lyra 等实现作设计依据。完整代码表达／审核规则按需查 AAADocs/Architecture/CodeConventions.md，不逐函数生成报告。
