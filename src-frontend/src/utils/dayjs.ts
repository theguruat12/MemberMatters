import dayjs from 'dayjs';
import localeData from 'dayjs/plugin/localeData';
import localizedFormat from 'dayjs/plugin/localizedFormat';

// Extend dayjs with locale plugins
dayjs.extend(localeData);
dayjs.extend(localizedFormat);

/**
 * Lazy‑load the locale that matches the user agent.
 * Returns a promise that resolves when the locale is loaded and set.
 */
export function initDayjsLocale() {
  const userLocale = navigator.language || 'en';
  const localeKey = userLocale.split('-')[0]; // e.g., 'en', 'fr'

  return import(`dayjs/locale/${localeKey}`)
    .then(() => {
      dayjs.locale(userLocale);
    })
    .catch(() => {
      // Fallback to English if the specific locale fails to load
      return import('dayjs/locale/en').then(() => {
        dayjs.locale('en');
      });
    });
}

export default dayjs;
