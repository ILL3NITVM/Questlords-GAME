/* Lightweight transient alert layer. Self-mounts a single #toast node. */
export function createToast() {
  let el = null, timer = null;
  function ensure() {
    el = document.getElementById("toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "toast";
      el.className = "toast";
      document.body.appendChild(el);
    }
  }
  return function toast(msg, cls = "") {
    ensure();
    el.textContent = msg;
    el.className = "toast on " + cls;
    clearTimeout(timer);
    timer = setTimeout(() => { el.className = "toast " + cls; }, 1900);
  };
}
