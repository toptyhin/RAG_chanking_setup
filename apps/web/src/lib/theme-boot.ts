/** Inline in <head> to avoid flash before hydration. Keep free of "use client". */
export const THEME_STORAGE_KEY = "rageval-theme";

export const THEME_BOOT_SCRIPT = `(function(){try{var k=${JSON.stringify(THEME_STORAGE_KEY)};var p=localStorage.getItem(k);var d=window.matchMedia("(prefers-color-scheme: dark)").matches;var dark=p==="dark"||(p!=="light"&&d);document.documentElement.classList.toggle("dark",dark);}catch(e){}})();`;
