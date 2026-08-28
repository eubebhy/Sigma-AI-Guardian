# Agent Runtime

## Quy ước

- `AgentRuntime` là public entry point cho lifecycle, command và config runtime.
- `FeatureRegistry` chỉ đăng ký feature có state hoặc lifecycle (`Service`, `Resource`).
- Stateless API không vào `FeatureRegistry`; đăng ký tại `CommandApi` với `feature=None`.
- Command và feature dùng `CommandName` và `FeatureName`, không dùng string identifier trực tiếp.

## Vai trò package

- `agent_runtime.py`: điều phối Runtime.
- `command_api.py`: khai báo command, dependency feature và handler.
- `feature_registry.py`: danh mục feature và factory tạo feature.
- `feature_manager.py`: tạo, giữ, lấy và shutdown feature.
- `request_types.py`: contract request, response, command và trạng thái.

## Cập nhật config

Service gọi `AgentRuntime.update_config()`. Runtime chuyển việc áp dụng config cho
`FeatureManager`; Registry không xử lý config update.
