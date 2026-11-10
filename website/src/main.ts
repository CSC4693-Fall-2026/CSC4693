import './style.css';

const VIZ_URL =
  'https://public.tableau.com/views/Week10-RoleDistPayPerCampus/Campus-Role';

const viz = document.querySelector('tableau-viz')!;
const loading = document.querySelector<HTMLDivElement>('#viz-loading')!;

async function init(): Promise<void> {
  await customElements.whenDefined('tableau-viz');

  viz.addEventListener('firstinteractive', () => {
    loading.hidden = true;
  }, { once: true });

  viz.addEventListener('vizloaderror', () => {
    loading.textContent = 'The chart could not be loaded.';
  });

  viz.src = VIZ_URL;
}

void init();
