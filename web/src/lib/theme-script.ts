import { THEME_STORAGE_KEY } from "@/stores/ui-store";

/**
 * Script chạy đồng bộ trong <head> trước khi trình duyệt vẽ, đặt data-theme
 * để không bị nhấp nháy sai chế độ khi tải trang. Mặc định sáng: chỉ tối khi
 * người dùng đã chủ động chọn "dark" (không theo prefers-color-scheme).
 */
export const themeInitScript = `(function(){var d=document.documentElement;var t=null;try{t=localStorage.getItem(${JSON.stringify(
  THEME_STORAGE_KEY,
)})}catch(e){}var dark=t==="dark";d.dataset.theme=dark?"dark":"light"})();`;
