import { onMounted, onBeforeUnmount } from 'vue';

export function useCtrlF(selector: string) {
  function handleCtrlF(e: KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
      e.preventDefault();
      const input = document.querySelector(selector) as HTMLInputElement;
      input?.focus();
    }
  }

  onMounted(() => window.addEventListener('keydown', handleCtrlF));
  onBeforeUnmount(() => window.removeEventListener('keydown', handleCtrlF));
}
