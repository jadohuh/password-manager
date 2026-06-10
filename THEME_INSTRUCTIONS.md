How to switch themes in this app
=================================

Quick (devtools)
- Open the site in your browser.
- In DevTools console or Elements panel, set the attribute on the `<html>` element:

  document.documentElement.setAttribute('data-theme', 'teal')

Available values: `teal`, `slate`, `violet`. Omitting the attribute uses the default palette.

Persistent client-side picker (drop into `base.html`)
--------------------------------------------------
You can add a small theme picker to the header and persist the choice in `localStorage`.

HTML (place inside the nav area):

<select id="theme-select" aria-label="Theme picker">
  <option value="">Default</option>
  <option value="teal">Teal</option>
  <option value="slate">Slate</option>
  <option value="violet">Violet</option>
</select>

JS (place before `</body>` or in a small script file):

<script>
  (function(){
    const select = document.getElementById('theme-select');
    if(!select) return;
    const saved = localStorage.getItem('theme');
    if(saved) document.documentElement.setAttribute('data-theme', saved);
    select.value = saved || '';
    select.addEventListener('change', (e) => {
      const v = e.target.value;
      if(v) document.documentElement.setAttribute('data-theme', v);
      else document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('theme', v);
    });
  })();
</script>

Server-side option (Flask)
--------------------------
- Set a session value on login or via a settings route and render the attribute on `<html>` in `base.html`:

  <html {% raw %}data-theme="{{ session.get('theme','') }}"{% endraw %}>

Pick the approach you prefer. If you want, I can implement the picker in `base.html` and add the small script and styling.
