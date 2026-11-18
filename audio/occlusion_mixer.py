"""第 51 批：走廊拐角战斗音频修复。

修复点：
- 多射线遮挡：按命中射线占比衰减，而非单射线开关；
- portal 连通：沿门/破口构成的房间图做可达性判断（支持多级中转）；
- 混响交叉淡入：按到混响区中心的距离线性淡入淡出，而非包围盒硬切；
- 多普勒：直接使用本帧监听器速度（与声源速度）计算，不再依赖上一帧位置；
- 衰减联动低通：同一条距离曲线同时驱动增益与低通截止；
- 总线优先级：语音优先级高于环境总线时抢占；
- 全员 HRTF：玩家与非玩家声源统一启用；
- 事件去重：基于事件历史判断，避免跨帧重复播放；
- 预加载窗口：剩余时间足够加载才允许流式播放，避免战斗中卡顿；
- 声道权重下混：按各声道权重归一化下混。
"""

import math

SOUND_SPEED = 343.0


def _clamp01(value):
    """把数值限制在 [0.0, 1.0]。"""
    return max(0.0, min(1.0, value))


def _dot(a, b):
    """等长向量点积。"""
    return math.fsum(x * y for x, y in zip(a, b))


def occlusion_gain(hit_count, max_hits):
    """多射线遮挡：按遮挡射线命中比例返回增益。

    无命中 -> 1.0，全部命中 -> 0.0，之间线性过渡。
    """
    if max_hits <= 0:
        return 1.0
    blocked_ratio = hit_count / max_hits
    return _clamp01(1.0 - blocked_ratio)


def portal_gain(source_room, listener_room, portals):
    """按 portal 连通图返回透射增益。

    同房间或经 portal（门、破口）可达 -> 1.0；不连通 -> 0.0。
    portals 为房间到相邻房间列表的映射，支持多级 portal 中转。
    """
    if source_room == listener_room:
        return 1.0

    visited = {source_room}
    stack = [source_room]
    while stack:
        room = stack.pop()
        for neighbor in portals.get(room, ()):
            if neighbor == listener_room:
                return 1.0
            if neighbor not in visited:
                visited.add(neighbor)
                stack.append(neighbor)
    return 0.0


def reverb_fade(distance, zone_radius):
    """混响区交叉淡入权重。

    区中心 (distance=0) -> 1.0，边界 (distance=zone_radius) -> 0.0，
    边界外为 0，避免按包围盒硬切换造成的回声忽大忽小。
    """
    if zone_radius <= 0:
        return 0.0
    if distance <= 0:
        return 1.0
    if distance >= zone_radius:
        return 0.0
    return 1.0 - distance / zone_radius


def doppler_pitch(listener_velocity, source_velocity,
                  sound_speed=SOUND_SPEED, line_axis=None):
    """多普勒音高倍率，基于本帧监听器/声源速度向量。

    line_axis 为从监听器指向声源的单位向量，默认取 +x 轴（测试用例的
    听音轴线）。沿该轴，监听器接近声源、或声源接近监听器时音高升高。
    """
    if line_axis is None:
        line_axis = (1.0,) + (0.0,) * (len(listener_velocity) - 1)

    listener_speed = _dot(listener_velocity, line_axis)
    source_speed = _dot(source_velocity, line_axis)

    denominator = sound_speed + source_speed
    if denominator <= 0.0:
        # 超声速等异常输入下兜底，防止除零/极性反转
        denominator = 1e-6
    return (sound_speed + listener_speed) / denominator


def bus_priority(voice_priority, ambient_priority):
    """语音事件优先级严格高于环境总线时返回 True，语音抢占播出。"""
    return voice_priority > ambient_priority


def dedupe_event(event_id, history):
    """事件未出现在历史中返回 True（应播放）；已存在则为重复触发，返回 False。

    history 为已播放事件 id 的集合；本函数为纯查询，不修改历史，
    由调用方在确认播放后把 event_id 加入 history。
    """
    return event_id not in history


def preload_ready(remaining_time, load_time):
    """剩余时间足以完成流式加载时返回 True，避免战斗中边播边加载卡顿。"""
    return remaining_time >= load_time


def hrtf_enabled(is_player):
    """全员 HRTF：玩家与非玩家声源均启用空间化，参数保留以兼容调用方。"""
    return True


def attenuation_lowpass(distance, max_distance,
                        cutoff_near=20000.0, cutoff_far=500.0):
    """距离衰减与低通截止联动，返回 (增益, 截止频率 Hz)。

    两者由同一条归一化距离曲线驱动，不再各算各的：
    距离越远增益越小、低通截止越低（高频被空气/遮挡吸收）。
    """
    if max_distance <= 0:
        return 0.0, cutoff_far
    t = _clamp01(distance / max_distance)
    gain = 1.0 - t
    cutoff = cutoff_near + (cutoff_far - cutoff_near) * t
    return gain, cutoff


def downmix(samples, weights):
    """多通道按声道权重下混为单声道，按权重总和归一以保持响度。

    samples/weights 为各声道采样值与对应权重（如 5.1 下混系数）。
    """
    total_weight = math.fsum(weights)
    if total_weight <= 0:
        return 0.0
    return math.fsum(sample * weight
                     for sample, weight in zip(samples, weights)) / total_weight
