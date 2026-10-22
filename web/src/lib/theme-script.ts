import { THEME_STORAGE_KEY } from "@/stores/ui-store";

/**
 * Script chạy đồng bộ trong <head> trước khi trình duyệt vẽ, đặt data-theme
 * để không bị nhấp nháy sai chế độ khi tải trang.
 */
export const themeInitScript = `(function(){var d=document.documentElement;var t=null;try{t=localStorage.getItem(${JSON.stringify(
  THEME_STORAGE_KEY,
)})}catch(e){}var dark=t==="dark"||(t!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);d.dataset.theme=dark?"dark":"light"})();`;
