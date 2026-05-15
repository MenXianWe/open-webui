export const DEFAULT_TEXT_SCALE = 1;

export const setTextScale = (scale) => {
	if (typeof document === 'undefined') {
		return;
	}

	document.documentElement.style.setProperty('--app-text-scale', `${scale}`);
};
