/* global browser */
const seek = document.getElementById("seek");
const status = document.getElementById("status");
let savedValue = true;

seek.onchange = async () => {
  seek.disabled = true;
  status.className = "";
  status.textContent = "Saving…";
  try {
    await browser.storage.local.set({ seekToCurrentPosition: seek.checked });
    savedValue = seek.checked;
    status.textContent = "Saved. Applies to new downloads.";
  } catch {
    seek.checked = savedValue;
    status.className = "error";
    status.textContent = "Could not save the preference. Try again.";
  } finally {
    seek.disabled = false;
  }
};

(async () => {
  try {
    const { seekToCurrentPosition } = await browser.storage.local.get({ seekToCurrentPosition: true });
    savedValue = !!seekToCurrentPosition;
    seek.checked = savedValue;
    seek.disabled = false;
    status.textContent = "Changes are saved automatically.";
  } catch {
    status.className = "error";
    status.textContent = "Could not load preferences. Reopen this page to try again.";
  }
})();
