/** Inline in <head> to set lang before hydration. Keep free of "use client". */
export const LOCALE_STORAGE_KEY = "rageval-locale";

export const LOCALE_BOOT_SCRIPT = `(function(){try{var k=${JSON.stringify(LOCALE_STORAGE_KEY)};var p=localStorage.getItem(k);if(p==="ru"||p==="en"){document.documentElement.lang=p;}}catch(e){}})();`;
