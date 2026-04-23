(function () {
    const MAX_PREVIEW_SIZE = { width: 1280, height: 850 };
    const PREVIEW_JPEG_QUALITY = 0.84;
    const DOWNLOAD_JPEG_QUALITY = 0.95;
    const DEFAULT_SETTINGS = {
        mode: "auto",
        percentile: 0.5,
        exposure: 0.0,
        white_balance: 0,
        contrast: 0,
        saturation: 0,
        clarity: 0,
        red_tint: 0,
        green_tint: 0,
        blue_tint: 0,
    };
    const PRESETS = {
        warm: { red_tint: 18, green_tint: 4, blue_tint: -12 },
        cool: { red_tint: -12, green_tint: 0, blue_tint: 18 },
        neutral: { red_tint: 0, green_tint: 0, blue_tint: 0 },
    };

    const state = {
        sessionId: null,
        images: [],
        currentIndex: -1,
        hasPendingChanges: false,
    };

    const fileInput = document.getElementById("fileInput");
    const uploadButton = document.getElementById("uploadButton");
    const clearButton = document.getElementById("clearButton");
    const statusText = document.getElementById("statusText");
    const counterText = document.getElementById("counterText");
    const currentName = document.getElementById("currentName");
    const imageList = document.getElementById("imageList");
    const prevButton = document.getElementById("prevButton");
    const nextButton = document.getElementById("nextButton");
    const downloadCurrentButton = document.getElementById("downloadCurrentButton");
    const downloadZipButton = document.getElementById("downloadZipButton");
    const resetButton = document.getElementById("resetButton");
    const applyAllButton = document.getElementById("applyAllButton");
    const applySettingsButton = document.getElementById("applySettingsButton");
    const undoButton = document.getElementById("undoButton");
    const pendingIndicator = document.getElementById("pendingIndicator");
    const presetWarmButton = document.getElementById("presetWarmButton");
    const presetCoolButton = document.getElementById("presetCoolButton");
    const presetNeutralButton = document.getElementById("presetNeutralButton");
    const tabButtons = document.querySelectorAll(".tab-button");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const modeSelect = document.getElementById("modeSelect");
    const percentileRange = document.getElementById("percentileRange");
    const percentileInput = document.getElementById("percentileInput");
    const exposureRange = document.getElementById("exposureRange");
    const exposureInput = document.getElementById("exposureInput");
    const whiteBalanceRange = document.getElementById("whiteBalanceRange");
    const whiteBalanceInput = document.getElementById("whiteBalanceInput");
    const contrastRange = document.getElementById("contrastRange");
    const contrastInput = document.getElementById("contrastInput");
    const saturationRange = document.getElementById("saturationRange");
    const saturationInput = document.getElementById("saturationInput");
    const clarityRange = document.getElementById("clarityRange");
    const clarityInput = document.getElementById("clarityInput");
    const redTintRange = document.getElementById("redTintRange");
    const redTintInput = document.getElementById("redTintInput");
    const greenTintRange = document.getElementById("greenTintRange");
    const greenTintInput = document.getElementById("greenTintInput");
    const blueTintRange = document.getElementById("blueTintRange");
    const blueTintInput = document.getElementById("blueTintInput");
    const percentileBadge = document.getElementById("percentileBadge");
    const exposureBadge = document.getElementById("exposureBadge");
    const whiteBalanceBadge = document.getElementById("whiteBalanceBadge");
    const contrastBadge = document.getElementById("contrastBadge");
    const saturationBadge = document.getElementById("saturationBadge");
    const clarityBadge = document.getElementById("clarityBadge");
    const redTintBadge = document.getElementById("redTintBadge");
    const greenTintBadge = document.getElementById("greenTintBadge");
    const blueTintBadge = document.getElementById("blueTintBadge");
    const originalImage = document.getElementById("originalImage");
    const previewImage = document.getElementById("previewImage");
    const processingOverlay = document.getElementById("processingOverlay");
    const processingText = document.getElementById("processingText");
    const originalScanToggle = document.getElementById("originalScanToggle");
    const viewer = document.querySelector(".viewer");

    let previewRequestId = 0;

    function clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    function clampByte(value) {
        return clamp(Math.round(value), 0, 255);
    }

    function cloneSettings(settings) {
        return {
            mode: settings.mode,
            percentile: Number(settings.percentile),
            exposure: Number(settings.exposure),
            white_balance: Number(settings.white_balance),
            contrast: Number(settings.contrast),
            saturation: Number(settings.saturation),
            clarity: Number(settings.clarity),
            red_tint: Number(settings.red_tint),
            green_tint: Number(settings.green_tint),
            blue_tint: Number(settings.blue_tint),
        };
    }

    function currentImage() {
        if (state.currentIndex < 0 || state.currentIndex >= state.images.length) {
            return null;
        }
        return state.images[state.currentIndex];
    }

    function setStatus(message) {
        statusText.textContent = message;
    }

    function activateTab(name) {
        tabButtons.forEach((button) => {
            const isActive = button.dataset.tab === name;
            button.classList.toggle("active", isActive);
            button.setAttribute("aria-selected", isActive ? "true" : "false");
        });
        tabPanels.forEach((panel) => {
            panel.classList.toggle("active", panel.dataset.panel === name);
        });
    }

    function setPendingChanges(isPending) {
        state.hasPendingChanges = isPending;
        pendingIndicator.classList.toggle("visible", isPending);
        updateButtons();
    }

    function markPendingChanges() {
        if (!currentImage()) {
            return;
        }
        setPendingChanges(true);
        setStatus("Changes staged. Click Apply Settings to process.");
    }

    function setProcessingState(isProcessing, message = "Processing preview...") {
        processingOverlay.classList.toggle("visible", isProcessing);
        processingText.textContent = message;
    }

    function clampValue(value, min, max, fallback) {
        const parsed = Number(value);
        if (!Number.isFinite(parsed)) {
            return fallback;
        }
        return clamp(parsed, min, max);
    }

    function setPercentileValue(value) {
        const normalized = clampValue(value, 0, 5, 0.5).toFixed(1);
        percentileRange.value = normalized;
        percentileInput.value = normalized;
        percentileBadge.textContent = normalized;
    }

    function setExposureValue(value) {
        const normalized = clampValue(value, -4, 4, 0).toFixed(1);
        exposureRange.value = normalized;
        exposureInput.value = normalized;
        exposureBadge.textContent = normalized;
    }

    function setWhiteBalanceValue(value) {
        const normalized = Math.round(clampValue(value, -100, 100, 0));
        whiteBalanceRange.value = normalized;
        whiteBalanceInput.value = normalized;
        whiteBalanceBadge.textContent = normalized;
    }

    function setContrastValue(value) {
        const normalized = Math.round(clampValue(value, -100, 100, 0));
        contrastRange.value = normalized;
        contrastInput.value = normalized;
        contrastBadge.textContent = `${normalized}%`;
    }

    function setSaturationValue(value) {
        const normalized = Math.round(clampValue(value, -100, 100, 0));
        saturationRange.value = normalized;
        saturationInput.value = normalized;
        saturationBadge.textContent = `${normalized}%`;
    }

    function setClarityValue(value) {
        const normalized = Math.round(clampValue(value, -100, 100, 0));
        clarityRange.value = normalized;
        clarityInput.value = normalized;
        clarityBadge.textContent = `${normalized}%`;
    }

    function setTintValue(rangeElement, inputElement, badgeElement, value) {
        const normalized = Math.round(clampValue(value, -100, 100, 0));
        rangeElement.value = normalized;
        inputElement.value = normalized;
        badgeElement.textContent = `${normalized}%`;
    }

    function currentSettings() {
        return {
            mode: modeSelect.value,
            percentile: Number(percentileRange.value),
            exposure: Number(exposureRange.value),
            white_balance: Number(whiteBalanceRange.value),
            contrast: Number(contrastRange.value),
            saturation: Number(saturationRange.value),
            clarity: Number(clarityRange.value),
            red_tint: Number(redTintRange.value),
            green_tint: Number(greenTintRange.value),
            blue_tint: Number(blueTintRange.value),
        };
    }

    function applySettings(settings) {
        const normalized = { ...DEFAULT_SETTINGS, ...settings };
        modeSelect.value = normalized.mode;
        setPercentileValue(normalized.percentile);
        setExposureValue(normalized.exposure);
        setWhiteBalanceValue(normalized.white_balance);
        setContrastValue(normalized.contrast);
        setSaturationValue(normalized.saturation);
        setClarityValue(normalized.clarity);
        setTintValue(redTintRange, redTintInput, redTintBadge, normalized.red_tint);
        setTintValue(greenTintRange, greenTintInput, greenTintBadge, normalized.green_tint);
        setTintValue(blueTintRange, blueTintInput, blueTintBadge, normalized.blue_tint);
    }

    function updateButtons() {
        const hasSession = state.images.length > 0;
        const hasImage = Boolean(currentImage());
        const hasPreviousSettings = hasImage && currentImage().previous_settings !== null && currentImage().previous_settings !== undefined;
        prevButton.disabled = !hasSession || state.currentIndex <= 0;
        nextButton.disabled = !hasSession || state.currentIndex >= state.images.length - 1;
        downloadCurrentButton.disabled = !hasImage;
        downloadZipButton.disabled = !hasSession;
        resetButton.disabled = !hasImage;
        applyAllButton.disabled = !hasImage;
        applySettingsButton.disabled = !hasImage || !state.hasPendingChanges;
        undoButton.disabled = !hasPreviousSettings;
        presetWarmButton.disabled = !hasImage;
        presetCoolButton.disabled = !hasImage;
        presetNeutralButton.disabled = !hasImage;
        if (!hasImage) {
            pendingIndicator.classList.remove("visible");
        }
    }

    function renderImageList() {
        imageList.innerHTML = "";
        state.images.forEach((image, index) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "image-chip" + (index === state.currentIndex ? " active" : "");
            button.textContent = `${index + 1}. ${image.filename}`;
            button.addEventListener("click", () => selectImage(index));
            imageList.appendChild(button);
        });
    }

    function updateMeta() {
        counterText.textContent = `${state.images.length} image${state.images.length === 1 ? "" : "s"}`;
        const image = currentImage();
        currentName.textContent = image ? image.filename : "No selection";
    }

    function fitSize(width, height, maxSize) {
        if (!maxSize) {
            return { width, height };
        }

        const ratio = Math.min(maxSize.width / width, maxSize.height / height, 1);
        return {
            width: Math.max(1, Math.round(width * ratio)),
            height: Math.max(1, Math.round(height * ratio)),
        };
    }

    async function decodeImageSource(file) {
        if (typeof createImageBitmap === "function") {
            try {
                const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
                return {
                    width: bitmap.width,
                    height: bitmap.height,
                    draw(context, width, height) {
                        context.drawImage(bitmap, 0, 0, width, height);
                    },
                    close() {
                        if (typeof bitmap.close === "function") {
                            bitmap.close();
                        }
                    },
                };
            } catch (error) {
            }
        }

        return await new Promise((resolve, reject) => {
            const image = new Image();
            const objectUrl = URL.createObjectURL(file);
            image.onload = () => {
                resolve({
                    width: image.naturalWidth,
                    height: image.naturalHeight,
                    draw(context, width, height) {
                        context.drawImage(image, 0, 0, width, height);
                    },
                    close() {
                        URL.revokeObjectURL(objectUrl);
                    },
                });
            };
            image.onerror = () => {
                URL.revokeObjectURL(objectUrl);
                reject(new Error(`Failed to decode ${file.name}`));
            };
            image.src = objectUrl;
        });
    }

    async function drawFileToCanvas(file, maxSize) {
        const source = await decodeImageSource(file);
        const target = fitSize(source.width, source.height, maxSize);
        const canvas = document.createElement("canvas");
        canvas.width = target.width;
        canvas.height = target.height;
        const context = canvas.getContext("2d", { willReadFrequently: true });
        source.draw(context, target.width, target.height);
        source.close();
        return canvas;
    }

    function isProbablyGrayscale(data) {
        const stride = Math.max(4, Math.floor((data.length / 4) / 2048) * 4);
        for (let index = 0; index < data.length; index += stride) {
            const red = data[index];
            const green = data[index + 1];
            const blue = data[index + 2];
            if (Math.abs(red - green) > 2 || Math.abs(red - blue) > 2 || Math.abs(green - blue) > 2) {
                return false;
            }
        }
        return true;
    }

    function percentileThreshold(histogram, total, percentile) {
        const target = total * (percentile / 100);
        let running = 0;
        for (let value = 0; value < histogram.length; value += 1) {
            running += histogram[value];
            if (running >= target) {
                return value;
            }
        }
        return histogram.length - 1;
    }

    function invertedChannelThresholds(data, percentile) {
        const histograms = [new Uint32Array(256), new Uint32Array(256), new Uint32Array(256)];
        const pixelCount = data.length / 4;
        for (let index = 0; index < data.length; index += 4) {
            histograms[0][255 - data[index]] += 1;
            histograms[1][255 - data[index + 1]] += 1;
            histograms[2][255 - data[index + 2]] += 1;
        }

        return histograms.map((histogram) => ({
            low: percentileThreshold(histogram, pixelCount, percentile),
            high: percentileThreshold(histogram, pixelCount, 100 - percentile),
        }));
    }

    function stretchValue(value, low, high) {
        if (high <= low) {
            return value;
        }
        return clampByte(((value - low) / (high - low)) * 255);
    }

    function applyExposureAndTints(red, green, blue, settings) {
        let nextRed = red;
        let nextGreen = green;
        let nextBlue = blue;
        const warmShift = (clamp(settings.white_balance, -100, 100) / 100) * 0.4;
        nextRed *= 1 + warmShift;
        nextBlue *= 1 - warmShift;

        const exposureMultiplier = 2 ** clamp(settings.exposure, -4, 4);
        nextRed *= exposureMultiplier;
        nextGreen *= exposureMultiplier;
        nextBlue *= exposureMultiplier;

        nextRed *= 1 + clamp(settings.red_tint, -100, 100) / 100;
        nextGreen *= 1 + clamp(settings.green_tint, -100, 100) / 100;
        nextBlue *= 1 + clamp(settings.blue_tint, -100, 100) / 100;

        return [clampByte(nextRed), clampByte(nextGreen), clampByte(nextBlue)];
    }

    function applyContrast(data, contrast) {
        if (!contrast) {
            return;
        }
        const factor = 1 + clamp(contrast, -100, 100) / 100;
        for (let index = 0; index < data.length; index += 4) {
            data[index] = clampByte((data[index] - 128) * factor + 128);
            data[index + 1] = clampByte((data[index + 1] - 128) * factor + 128);
            data[index + 2] = clampByte((data[index + 2] - 128) * factor + 128);
        }
    }

    function applySaturation(data, saturation) {
        if (!saturation) {
            return;
        }
        const factor = 1 + clamp(saturation, -100, 100) / 100;
        for (let index = 0; index < data.length; index += 4) {
            const red = data[index];
            const green = data[index + 1];
            const blue = data[index + 2];
            const gray = red * 0.299 + green * 0.587 + blue * 0.114;
            data[index] = clampByte(gray + (red - gray) * factor);
            data[index + 1] = clampByte(gray + (green - gray) * factor);
            data[index + 2] = clampByte(gray + (blue - gray) * factor);
        }
    }

    function gaussianBlur(data, width, height) {
        const blurred = new Uint8ClampedArray(data.length);
        const kernel = [1, 2, 1, 2, 4, 2, 1, 2, 1];
        const offsets = [
            [-1, -1], [0, -1], [1, -1],
            [-1, 0], [0, 0], [1, 0],
            [-1, 1], [0, 1], [1, 1],
        ];

        for (let y = 0; y < height; y += 1) {
            for (let x = 0; x < width; x += 1) {
                let red = 0;
                let green = 0;
                let blue = 0;
                let weight = 0;
                for (let kernelIndex = 0; kernelIndex < offsets.length; kernelIndex += 1) {
                    const sampleX = clamp(x + offsets[kernelIndex][0], 0, width - 1);
                    const sampleY = clamp(y + offsets[kernelIndex][1], 0, height - 1);
                    const dataIndex = (sampleY * width + sampleX) * 4;
                    const factor = kernel[kernelIndex];
                    red += data[dataIndex] * factor;
                    green += data[dataIndex + 1] * factor;
                    blue += data[dataIndex + 2] * factor;
                    weight += factor;
                }

                const outputIndex = (y * width + x) * 4;
                blurred[outputIndex] = clampByte(red / weight);
                blurred[outputIndex + 1] = clampByte(green / weight);
                blurred[outputIndex + 2] = clampByte(blue / weight);
                blurred[outputIndex + 3] = data[outputIndex + 3];
            }
        }

        return blurred;
    }

    function applyClarity(data, width, height, clarity) {
        if (!clarity) {
            return;
        }
        const amount = Math.abs(clamp(clarity, -100, 100)) / 100;
        const blurred = gaussianBlur(data, width, height);

        for (let index = 0; index < data.length; index += 4) {
            if (clarity > 0) {
                const percent = 80 + amount * 170;
                const strength = percent / 100;
                const threshold = 2;

                const diffRed = data[index] - blurred[index];
                const diffGreen = data[index + 1] - blurred[index + 1];
                const diffBlue = data[index + 2] - blurred[index + 2];

                data[index] = Math.abs(diffRed) >= threshold
                    ? clampByte(data[index] + diffRed * strength)
                    : data[index];
                data[index + 1] = Math.abs(diffGreen) >= threshold
                    ? clampByte(data[index + 1] + diffGreen * strength)
                    : data[index + 1];
                data[index + 2] = Math.abs(diffBlue) >= threshold
                    ? clampByte(data[index + 2] + diffBlue * strength)
                    : data[index + 2];
            } else {
                const alpha = amount * 0.35;
                data[index] = clampByte(data[index] * (1 - alpha) + blurred[index] * alpha);
                data[index + 1] = clampByte(data[index + 1] * (1 - alpha) + blurred[index + 1] * alpha);
                data[index + 2] = clampByte(data[index + 2] * (1 - alpha) + blurred[index + 2] * alpha);
            }
        }
    }

    function processColorImage(imageData, settings) {
        const data = imageData.data;
        const thresholds = invertedChannelThresholds(data, clamp(settings.percentile, 0, 5));

        for (let index = 0; index < data.length; index += 4) {
            const invertedRed = 255 - data[index];
            const invertedGreen = 255 - data[index + 1];
            const invertedBlue = 255 - data[index + 2];
            const stretchedRed = stretchValue(invertedRed, thresholds[0].low, thresholds[0].high);
            const stretchedGreen = stretchValue(invertedGreen, thresholds[1].low, thresholds[1].high);
            const stretchedBlue = stretchValue(invertedBlue, thresholds[2].low, thresholds[2].high);
            const adjusted = applyExposureAndTints(stretchedRed, stretchedGreen, stretchedBlue, settings);
            data[index] = adjusted[0];
            data[index + 1] = adjusted[1];
            data[index + 2] = adjusted[2];
            data[index + 3] = 255;
        }

        applyContrast(data, settings.contrast);
        applySaturation(data, settings.saturation);
        applyClarity(data, imageData.width, imageData.height, settings.clarity);
    }

    function processBwImage(imageData, settings) {
        const data = imageData.data;
        const multiplier = 2 ** clamp(settings.exposure, -4, 4);
        for (let index = 0; index < data.length; index += 4) {
            const gray = data[index] * 0.299 + data[index + 1] * 0.587 + data[index + 2] * 0.114;
            const inverted = clampByte((255 - gray) * multiplier);
            data[index] = inverted;
            data[index + 1] = inverted;
            data[index + 2] = inverted;
            data[index + 3] = 255;
        }

        applyContrast(data, settings.contrast);
        applyClarity(data, imageData.width, imageData.height, settings.clarity);
    }

    function processImageData(imageData, settings) {
        const mode = settings.mode || "auto";
        const shouldUseColor = mode === "color" || (mode === "auto" && !isProbablyGrayscale(imageData.data));
        if (shouldUseColor) {
            processColorImage(imageData, settings);
            return;
        }
        processBwImage(imageData, settings);
    }

    function canvasToBlob(canvas, mimeType, quality) {
        return new Promise((resolve, reject) => {
            canvas.toBlob((blob) => {
                if (!blob) {
                    reject(new Error("Failed to export processed image."));
                    return;
                }
                resolve(blob);
            }, mimeType, quality);
        });
    }

    async function renderProcessedBlob(file, settings, maxSize, quality) {
        const canvas = await drawFileToCanvas(file, maxSize);
        const context = canvas.getContext("2d", { willReadFrequently: true });
        const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
        processImageData(imageData, settings);
        context.putImageData(imageData, 0, 0);
        return await canvasToBlob(canvas, "image/jpeg", quality);
    }

    function revokePreviewUrl(image) {
        if (image && image.previewUrl) {
            URL.revokeObjectURL(image.previewUrl);
            image.previewUrl = null;
        }
    }

    function revokeSessionUrls() {
        state.images.forEach((image) => {
            if (image.originalUrl) {
                URL.revokeObjectURL(image.originalUrl);
            }
            revokePreviewUrl(image);
        });
    }

    async function refreshPreview() {
        const image = currentImage();
        if (!image) {
            originalImage.removeAttribute("src");
            previewImage.removeAttribute("src");
            setProcessingState(false);
            updateButtons();
            updateMeta();
            return;
        }

        originalImage.src = image.originalUrl;
        const settings = currentSettings();
        previewRequestId += 1;
        const requestId = previewRequestId;
        setProcessingState(true, "Processing preview...");
        setStatus(`Processing ${image.filename}...`);

        try {
            const previewBlob = await renderProcessedBlob(image.file, settings, MAX_PREVIEW_SIZE, PREVIEW_JPEG_QUALITY);
            if (requestId !== previewRequestId) {
                return;
            }

            revokePreviewUrl(image);
            image.previewUrl = URL.createObjectURL(previewBlob);
            previewImage.onload = () => {
                if (requestId !== previewRequestId) {
                    return;
                }
                setProcessingState(false);
                setStatus(`Preview ready for ${image.filename}`);
            };
            previewImage.onerror = () => {
                if (requestId !== previewRequestId) {
                    return;
                }
                setProcessingState(false);
                setStatus(`Preview failed for ${image.filename}`);
            };
            previewImage.src = image.previewUrl;
        } catch (error) {
            if (requestId !== previewRequestId) {
                return;
            }
            setProcessingState(false);
            setStatus(error.message || `Preview failed for ${image.filename}`);
        }

        renderImageList();
        updateButtons();
        updateMeta();
    }

    function imageFileName(filename) {
        const lastDot = filename.lastIndexOf(".");
        if (lastDot <= 0) {
            return { base: filename, extension: ".jpg" };
        }
        return {
            base: filename.slice(0, lastDot),
            extension: filename.slice(lastDot) || ".jpg",
        };
    }

    function triggerDownload(blob, filename) {
        const downloadUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
    }

    async function saveCurrentSettings() {
        const image = currentImage();
        if (!image) {
            return;
        }

        image.previous_settings = cloneSettings(image.settings);
        image.settings = cloneSettings(currentSettings());
        applySettings(image.settings);
        setPendingChanges(false);
        setStatus(`Saved settings for ${image.filename}`);
        renderImageList();
        updateButtons();
    }

    async function applyCurrentSettings() {
        await saveCurrentSettings();
        await refreshPreview();
    }

    function applySettingsObject(partialSettings) {
        const merged = {
            ...currentSettings(),
            ...partialSettings,
        };
        applySettings(merged);
        markPendingChanges();
    }

    function resetAdjustments() {
        if (!currentImage()) {
            return;
        }
        applySettings(DEFAULT_SETTINGS);
        markPendingChanges();
    }

    function undoSettings() {
        const image = currentImage();
        if (!image || !image.previous_settings) {
            return;
        }
        applySettings(image.previous_settings);
        markPendingChanges();
        setStatus("Settings reverted to previous state.");
    }

    async function applyCurrentToAll() {
        if (!currentImage()) {
            return;
        }

        const settings = cloneSettings(currentSettings());
        setStatus("Applying current settings to all images...");
        state.images = state.images.map((image) => ({
            ...image,
            previous_settings: cloneSettings(image.settings),
            settings: cloneSettings(settings),
        }));
        const selectedImage = currentImage();
        if (selectedImage) {
            applySettings(selectedImage.settings);
        }
        setPendingChanges(false);
        renderImageList();
        updateButtons();
        updateMeta();
        await refreshPreview();
        setStatus(`Applied current settings to ${state.images.length} image${state.images.length === 1 ? "" : "s"}.`);
    }

    function selectImage(index) {
        state.currentIndex = index;
        const image = currentImage();
        if (!image) {
            return;
        }
        applySettings(image.settings);
        setPendingChanges(false);
        refreshPreview();
        setStatus(`Reviewing ${image.filename}`);
    }

    async function uploadFiles() {
        if (!fileInput.files.length) {
            setStatus("Choose one or more images first.");
            return;
        }

        uploadButton.disabled = true;
        setStatus("Loading images locally...");

        try {
            revokeSessionUrls();
            state.sessionId = "local-session";
            state.images = Array.from(fileInput.files).map((file, index) => ({
                id: (typeof crypto !== "undefined" && crypto.randomUUID) ? crypto.randomUUID() : `image-${Date.now()}-${index}`,
                filename: file.name,
                file,
                originalUrl: URL.createObjectURL(file),
                previewUrl: null,
                settings: cloneSettings(DEFAULT_SETTINGS),
                previous_settings: null,
            }));
            state.currentIndex = state.images.length ? 0 : -1;
            renderImageList();
            if (state.currentIndex >= 0) {
                applySettings(state.images[0].settings);
                setPendingChanges(false);
                await refreshPreview();
            }
            updateButtons();
            updateMeta();
            setStatus(`Session ready with ${state.images.length} image${state.images.length === 1 ? "" : "s"}.`);
        } catch (error) {
            setStatus(error.message || "Upload failed.");
        } finally {
            uploadButton.disabled = false;
        }
    }

    function clearSession() {
        revokeSessionUrls();
        state.sessionId = null;
        state.images = [];
        state.currentIndex = -1;
        setPendingChanges(false);
        fileInput.value = "";
        renderImageList();
        refreshPreview();
        setStatus("Session cleared.");
    }

    function move(delta) {
        const nextIndex = state.currentIndex + delta;
        if (nextIndex < 0 || nextIndex >= state.images.length) {
            return;
        }
        selectImage(nextIndex);
    }

    async function downloadCurrent() {
        const image = currentImage();
        if (!image) {
            return;
        }
        if (state.hasPendingChanges) {
            setStatus("Apply Settings before downloading the current image.");
            return;
        }

        try {
            setStatus(`Rendering full-resolution download for ${image.filename}...`);
            const blob = await renderProcessedBlob(image.file, image.settings, null, DOWNLOAD_JPEG_QUALITY);
            const parts = imageFileName(image.filename);
            triggerDownload(blob, `${parts.base}_positive.jpg`);
            setStatus(`Downloaded ${image.filename}`);
        } catch (error) {
            setStatus(error.message || `Failed to download ${image.filename}`);
        }
    }

    async function downloadZip() {
        if (!state.images.length) {
            return;
        }
        if (state.hasPendingChanges) {
            setStatus("Apply Settings before downloading the ZIP.");
            return;
        }
        if (typeof JSZip === "undefined") {
            setStatus("ZIP export is unavailable because JSZip did not load.");
            return;
        }

        const zip = new JSZip();
        const manifest = [];
        for (let index = 0; index < state.images.length; index += 1) {
            const image = state.images[index];
            setStatus(`Packaging ${index + 1} of ${state.images.length}: ${image.filename}`);
            const blob = await renderProcessedBlob(image.file, image.settings, null, DOWNLOAD_JPEG_QUALITY);
            const outputName = `${imageFileName(image.filename).base}_positive.jpg`;
            zip.file(outputName, blob);
            manifest.push({
                id: image.id,
                filename: image.filename,
                output_filename: outputName,
                settings: cloneSettings(image.settings),
            });
        }
        zip.file("manifest.json", JSON.stringify({ images: manifest }, null, 2));
        const zipBlob = await zip.generateAsync({ type: "blob" });
        triggerDownload(zipBlob, "negative-review-lab-export.zip");
        setStatus(`Downloaded ZIP for ${state.images.length} image${state.images.length === 1 ? "" : "s"}.`);
    }

    originalScanToggle.addEventListener("click", () => {
        const isEnabled = originalScanToggle.classList.contains("enabled");
        originalScanToggle.classList.toggle("enabled", !isEnabled);
        originalScanToggle.setAttribute("aria-pressed", (!isEnabled) ? "true" : "false");
        viewer.classList.toggle("original-minimized", isEnabled);
    });

    uploadButton.addEventListener("click", uploadFiles);
    clearButton.addEventListener("click", clearSession);
    prevButton.addEventListener("click", () => move(-1));
    nextButton.addEventListener("click", () => move(1));
    downloadCurrentButton.addEventListener("click", downloadCurrent);
    downloadZipButton.addEventListener("click", downloadZip);
    resetButton.addEventListener("click", resetAdjustments);
    applyAllButton.addEventListener("click", applyCurrentToAll);
    applySettingsButton.addEventListener("click", applyCurrentSettings);
    undoButton.addEventListener("click", undoSettings);
    presetWarmButton.addEventListener("click", () => applySettingsObject(PRESETS.warm));
    presetCoolButton.addEventListener("click", () => applySettingsObject(PRESETS.cool));
    presetNeutralButton.addEventListener("click", () => applySettingsObject(PRESETS.neutral));

    percentileRange.addEventListener("input", () => {
        setPercentileValue(percentileRange.value);
        markPendingChanges();
    });
    percentileInput.addEventListener("input", () => {
        setPercentileValue(percentileInput.value);
        markPendingChanges();
    });
    exposureRange.addEventListener("input", () => {
        setExposureValue(exposureRange.value);
        markPendingChanges();
    });
    exposureInput.addEventListener("input", () => {
        setExposureValue(exposureInput.value);
        markPendingChanges();
    });
    whiteBalanceRange.addEventListener("input", () => {
        setWhiteBalanceValue(whiteBalanceRange.value);
        markPendingChanges();
    });
    whiteBalanceInput.addEventListener("input", () => {
        setWhiteBalanceValue(whiteBalanceInput.value);
        markPendingChanges();
    });
    contrastRange.addEventListener("input", () => {
        setContrastValue(contrastRange.value);
        markPendingChanges();
    });
    contrastInput.addEventListener("input", () => {
        setContrastValue(contrastInput.value);
        markPendingChanges();
    });
    saturationRange.addEventListener("input", () => {
        setSaturationValue(saturationRange.value);
        markPendingChanges();
    });
    saturationInput.addEventListener("input", () => {
        setSaturationValue(saturationInput.value);
        markPendingChanges();
    });
    clarityRange.addEventListener("input", () => {
        setClarityValue(clarityRange.value);
        markPendingChanges();
    });
    clarityInput.addEventListener("input", () => {
        setClarityValue(clarityInput.value);
        markPendingChanges();
    });
    redTintRange.addEventListener("input", () => {
        setTintValue(redTintRange, redTintInput, redTintBadge, redTintRange.value);
        markPendingChanges();
    });
    redTintInput.addEventListener("input", () => {
        setTintValue(redTintRange, redTintInput, redTintBadge, redTintInput.value);
        markPendingChanges();
    });
    greenTintRange.addEventListener("input", () => {
        setTintValue(greenTintRange, greenTintInput, greenTintBadge, greenTintRange.value);
        markPendingChanges();
    });
    greenTintInput.addEventListener("input", () => {
        setTintValue(greenTintRange, greenTintInput, greenTintBadge, greenTintInput.value);
        markPendingChanges();
    });
    blueTintRange.addEventListener("input", () => {
        setTintValue(blueTintRange, blueTintInput, blueTintBadge, blueTintRange.value);
        markPendingChanges();
    });
    blueTintInput.addEventListener("input", () => {
        setTintValue(blueTintRange, blueTintInput, blueTintBadge, blueTintInput.value);
        markPendingChanges();
    });
    modeSelect.addEventListener("change", markPendingChanges);

    tabButtons.forEach((button) => {
        button.addEventListener("click", () => {
            activateTab(button.dataset.tab);
        });
    });

    setPercentileValue(percentileRange.value);
    setExposureValue(exposureRange.value);
    setWhiteBalanceValue(whiteBalanceRange.value);
    setContrastValue(contrastRange.value);
    setSaturationValue(saturationRange.value);
    setClarityValue(clarityRange.value);
    setTintValue(redTintRange, redTintInput, redTintBadge, redTintRange.value);
    setTintValue(greenTintRange, greenTintInput, greenTintBadge, greenTintRange.value);
    setTintValue(blueTintRange, blueTintInput, blueTintBadge, blueTintRange.value);
    activateTab("adjustment");
    updateButtons();
    setPendingChanges(false);
    refreshPreview();
})();