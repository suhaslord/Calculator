from pathlib import Path

path = Path('tools/yoshii_copilot_win11.py')
src = path.read_text(encoding='utf-8')
old = '''def send(text):
    edit = wait_for_input(15)
    if edit is None:
        raise RuntimeError('InputTextBox missing')
    edit.click_input()
    time.sleep(1)
    try:
        edit.set_edit_text(text)
    except Exception:
        keyboard.send_keys('^a')
        keyboard.send_keys(text, with_spaces=True)
    print('SUBMIT', CASE_ID, CONDITION, repr(edit.window_text()))
    keyboard.send_keys('{ENTER}')
    time.sleep(3)
'''
new = '''def send(text):
    edit = wait_for_input(15)
    if edit is None:
        raise RuntimeError('InputTextBox missing')
    edit.click_input()
    time.sleep(1)
    try:
        edit.set_edit_text(text)
    except Exception:
        keyboard.send_keys('^a')
        keyboard.send_keys(text, with_spaces=True)
    print('SUBMIT_TEXT', CASE_ID, CONDITION, repr(edit.window_text()))
    submit = find('ComposerSubmitButton', 'Button')
    if submit is None:
        snapshot('submit_button_missing')
        raise RuntimeError('ComposerSubmitButton missing')
    invoke_or_click(submit, 'ComposerSubmitButton')
    deadline = time.time() + 20
    while time.time() < deadline:
        current = find('InputTextBox', 'Edit')
        if current is not None:
            value = current.window_text().strip()
            if not value or value != text.strip():
                print('SUBMIT_CONFIRMED', repr(value))
                time.sleep(2)
                return
        time.sleep(1)
    snapshot('submit_not_cleared')
    raise RuntimeError('Composer did not clear after submit')
'''
if old not in src:
    raise SystemExit('expected send() block not found')
exec(compile(src.replace(old, new), str(path), 'exec'), {'__name__': '__main__', '__file__': str(path)})
