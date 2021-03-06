const API_ENDPOINT = "http://localhost:8000/censored";
const BG_IMG_URL_PATTERN = /url\("(.*)"\)/;

const WHITELISTED_DOMAINS = [
    /(.*\.)?github\.com/,
    /(.*\.)?instagram\.com/
];

function base64url(plaintext) {
    return btoa(plaintext).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

function handleNewIMG(imgElem) {
    const imgUrl = imgElem.src;
    if (imgUrl) {
        imgElem.src = `${API_ENDPOINT}/${base64url(imgUrl)}`;
        imgElem.setAttribute("betamode", "1");
        imgElem.removeAttribute("srcset");
    } // TODO: handle images with no src
}

function handleNewBGIMG(imgElem) {
    const bgIMG = getComputedStyle(imgElem).backgroundImage;
    const match = bgIMG.match(BG_IMG_URL_PATTERN);
    const imgUrl = match.length > 1 ? match[1] : null;
    if (imgUrl) {
        imgElem.style.backgroundImage = `url("${API_ENDPOINT}/${base64url(imgUrl)}")`;
        imgElem.setAttribute("betamode", "1");
    }
}

function queueExistingImages() {
    findImagesRecursively(document.body).forEach(handleNewIMG);
    findBackgroundImagesRecursively(document.body).forEach(handleNewBGIMG);
}

function findImagesRecursively(element) {
    let images = [];
    if (element != null && element.nodeType === 1) {
        if (element.tagName === "IMG" && !element.hasAttribute("betamode"))
            images.push(element);

        for (const child of element.childNodes) {
            images = images.concat(findImagesRecursively(child));
        }
    }
    return images;
}

function findBackgroundImagesRecursively(element) {
    let images = [];
    if (element != null && element.nodeType === 1) {
        if (getComputedStyle(element).backgroundImage !== "none" && !element.hasAttribute("betamode"))
            images.push(element);

        for (const child of element.childNodes) {
            images = images.concat(findBackgroundImagesRecursively(child));
        }
    }
    return images;
}

for (const pattern of WHITELISTED_DOMAINS) {
    if (pattern.test(window.location.hostname)) {
        document.documentElement.setAttribute("betamode-cleared", "");
        break;
    }
}

if (!document.documentElement.hasAttribute("betamode-cleared")) {
    const config = {childList: true, subtree: true};

    const callback = function (mutationsList, observer) {
        for (const mutation of mutationsList) {
            if (mutation.type === "childList") {
                for (const e of mutation.addedNodes) {
                    findImagesRecursively(e).forEach(handleNewIMG);
                    findBackgroundImagesRecursively(e).forEach(handleNewBGIMG);
                }
            }
        }
    };

    const observer = new MutationObserver(callback);
    observer.observe(document, config);

    queueExistingImages();
}
