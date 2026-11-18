# pairwise-audio-occlusion

走廊拐角发生战斗时枪声从墙后直穿、回声忽大忽小：遮挡只做单射线；门和破口没有 portal 连通；混响区按包围盒切换没淡入；多普勒用监听器上一帧位置；距离衰减和低通截止分开算；语音优先级压不过环境总线；HRTF 只对玩家生效；声音事件跨帧累积导致重复播放；流式音频加载在战斗中卡顿；多通道下混没按声道权重。audio/occlusion_mixer.py 是核心，tests/test_occlusion_mixer.py 15个红。要修的是：多射线遮挡；portal 连通；混响交叉淡入；监听器速度；衰减联动低通；总线优先级；全员 HRTF；事件去重；预加载窗口；声道权重下混。

## 运行

```bash
python -m pytest tests -q
```

初始状态：15 个用例失败。修复实现使全部用例通过，不要修改 `tests/` 下的测试。

子方向：音视频处理；任务类型：Bugfix；语言/框架：Python 3, pytest；环境可复现等级：无外部依赖。
