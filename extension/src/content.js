const API_ENDPOINT = "http://localhost:8000/censored"

function base64url(plaintext) {
    return btoa(plaintext).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

function handleNewIMG(imgElem) {
    const imgUrl = imgElem.src;
    if (imgUrl) {
        imgElem.src = `${API_ENDPOINT}/${base64url(imgUrl)}`
        imgElem.setAttribute("betamode", "1");
        imgElem.removeAttribute("srcset");
    } // TODO: handle images with no src
}


function queueImages() {
    for (const e of document.querySelectorAll("img:not([betamode])")) {
        handleNewIMG(e);
    }
}

setInterval(queueImages, 500);
queueImages();
