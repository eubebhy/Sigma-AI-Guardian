# Linux Input Control

File path: `src/device_controler/input_controller/linux/README.md`

Vai tro: compatibility facade cho Linux input controller. Native implementation nam
tai `src/agent/platform/linux/input_controller/`: `types.py` mo ta UInput/XInput,
`utils.py` quan ly lifecycle, con `sendinput_kb.py` va `sendinput_mouse.py` phat
event. Package nay khong doc input vat ly; dung `utils.key_listener`.

`UInputManager.get_ui()` tra device cache con khoe, hoac dong device chet va tao
generation moi. `create_ui()` chi tra sau khi XInput2 thay device, tranh gui event
truoc khi Xorg/libinput attach xong. Health duoc cache 5 giay de thao tac nhanh
khong query X11 cho tung event.

Linux can `/dev/uinput`, quyen ghi, `DISPLAY`, Xorg va `xinput`. Chay manual control
co chu dich:

```bash
sudo env DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" \
  ./.pyvenv/bin/python tests/test_input_controller.py real control \
  --move-rel 10 0 --click left
```
