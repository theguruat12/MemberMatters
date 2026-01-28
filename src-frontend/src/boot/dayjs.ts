import { boot } from 'quasar/wrappers';
import { initDayjsLocale } from '../utils/dayjs';

// Initialise dayjs with the browser locale on app start
export default boot(({ app }) => {
  // Load locale asynchronously; the formatting functions will pick it up when called.
  initDayjsLocale();
});
