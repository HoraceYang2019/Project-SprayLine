# Drawer trigger toggle fix

This version fixes the vertical `通知工程師` drawer trigger.

## Behavior

- When the drawer is closed, clicking the vertical button opens the engineer notification panel.
- When the drawer is open, the same vertical button changes to `關閉面板` and clicking it closes the panel.
- The overlay and the internal `關閉` button still close the panel.
- After a notification Email is sent, the Email button is hidden and replaced with an `已送出通知 Email` message.
- Once the drawer is closed, the drawer content is rebuilt, so the Email button appears again when the drawer is opened next time.
