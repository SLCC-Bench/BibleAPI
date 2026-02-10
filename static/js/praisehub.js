document.addEventListener("DOMContentLoaded", function() {
    var tableData = [
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:1", verse: "Nang pasimula, nilikha ng Dios ang langit at ang lupa.", highlight: true},
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:2", verse: "Ang mundo noon ay wala pang anyo at balot ng kadiliman. Ang Espiritu ng Dios ay kumikilos sa ibabaw ng mga tubig."},
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:3", verse: "Sinabi ng Dios, Magkaroon ng liwanag! At nagkaroon ng liwanag."},
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:4", verse: "Nasiayhan ang Dios sa liwanag na nakita niya. Pagkatapos, inihiwalay ng Dios ang liwanag sa kadiliman."},
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:5", verse: "Tinawag niyang araw ang liwanag, at gabi naman ang kadiliman. Lumipas ang gabi at umaga. Iyon ang unang araw."},
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:6", verse: "Pagkatapos, sinabi ng Dios, Magkaroon ng pagitan na naghihiwalay sa tubig sa itaas at sa tubig sa ibaba."},
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:7", verse: "At nagkaroon nga ng pagitan na naghihiwalay sa tubig sa itaas at sa tubig sa ibaba."},
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:8", verse: "Ang pagitan ng tubig ay tinawag ng Dios na kalawakan. Lumipas ang gabi at dumating ang umaga. Iyon ang ikalawang araw."},
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:9", verse: "Pagkatapos, sinabi ng Dios, Magsama sa isang lugar ang tuyong bahagi; At iyon nga ang nangyari."},
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:10", verse: "Tinawag niyang lupa ang tuyong lugar, at dagat naman ang tinipong tubig. Nasiayhan ang Dios sa nakita niya."},
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:11", verse: "Sinabi ng Dios, Magusbong sa lupa ang mga tanim na nagbubunga ng butil, at mga punongkahoy na namumunga ayon sa kani-kanilang uri. At iyon nga ..."},
        {translation: "Ang Salita ng Dios", reference: "Genesis 1:12", verse: "Tubo sa lupa ang mga tanim at mga punongkahoy na namumunga ayon sa kani-kanilang uri. Nasiayhan ang Dios sa nakita niya."}
    ];
    var table = new Tabulator("#scripture-table", {
        data: tableData,
        layout: "fitColumns",
        columns: [
            {title: "Translation", field: "translation", headerSort: false},
            {title: "Reference", field: "reference", headerSort: false},
            {title: "Verse", field: "verse", headerSort: false},
        ],
        rowFormatter: function(row) {
            var data = row.getData();
            if (data.highlight) {
                row.getElement().style.backgroundColor = "#FEF3C7"; // bg-yellow-100
                row.getElement().style.fontWeight = "bold";
            }
        },
    });
});

document.addEventListener('contextmenu', function(e) {
    e.preventDefault();
});

document.getElementById('btn-live').addEventListener('click', async function() {
    // 1. Setup default positioning (Current Monitor)
    let left = window.screenX;
    let top = window.screenY;
    let width = 800;
    let height = 600;

    // 2. Try to detect Second Screen using Window Management API
    if ('getScreenDetails' in window) {
        try {
            const screenDetails = await window.getScreenDetails();
            // Find the first screen that is NOT the one the browser is currently on
            const secondaryScreen = screenDetails.screens.find(s => s !== screenDetails.currentScreen);

            if (secondaryScreen) {
                left = secondaryScreen.availLeft;
                top = secondaryScreen.availTop;
                width = secondaryScreen.availWidth;
                height = secondaryScreen.availHeight;
            }
        } catch (err) {
            console.error("Multi-screen permission denied or error:", err);
        }
    }

    // 3. Open the Live Window
    const features = `left=${left},top=${top},width=${width},height=${height},menubar=no,toolbar=no,location=no,status=no`;
    const win = window.open("", "PraisehubLive", features);

    if (win) {
        // Grab current live data
        const verseText = document.getElementById('live-slide-verse').innerText;
        const refText = document.getElementById('live-slide-ref').innerText;

        win.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Praisehub Live</title>
                <link href="https://fonts.googleapis.com/css2?family=Lexend:wght@700&display=swap" rel="stylesheet">
                <style>
                    body {
                        margin: 0;
                        background: #000;
                        color: #fff;
                        font-family: 'Lexend', sans-serif;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        overflow: hidden;
                        text-align: center;
                        cursor: none;
                    }
                    .container { padding: 40px; }
                    .verse { font-size: 4.5rem; line-height: 1.2; margin-bottom: 30px; }
                    .ref { font-size: 2rem; color: #facc15; }
                    .overlay-blur {
                        position: fixed;
                        top: 0; left: 0; width: 100vw; height: 100vh;
                        background: rgba(0,0,0,0.5);
                        backdrop-filter: blur(8px);
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        z-index: 9999;
                    }
                    .overlay-buttons {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        position: relative;
                    }
                    .fullscreen-btn {
                        background: #facc15;
                        color: #222;
                        font-size: 1.2rem;
                        font-weight: bold;
                        padding: 0.75rem 1.5rem;
                        border: none;
                        border-radius: 2rem;
                        box-shadow: 0 4px 32px rgba(0,0,0,0.2);
                        cursor: pointer;
                        transition: background 0.2s;
                        position: relative;
                    }
                    .fullscreen-btn:hover {
                        background: #ffe066;
                    }
                    .close-x-btn {
                        position: absolute;
                        top: 0.2rem;
                        right: 0.2rem;
                        background: #fff;
                        color: #222;
                        font-size: 1.2rem;
                        font-weight: bold;
                        width: 2rem;
                        height: 2rem;
                        border: none;
                        border-radius: 50%;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                        cursor: pointer;
                        display: none;
                        align-items: center;
                        justify-content: center;
                        transition: background 0.2s;
                        z-index: 10;
                    }
                    .fullscreen-btn:hover + .close-x-btn,
                    .close-x-btn:hover {
                        display: flex;
                    }
                    .close-x-btn:hover {
                        background: #e5e7eb;
                    }
                </style>
            </head>
            <body>
                <div class="container" id="main-content">
                    <div class="verse">${verseText}</div>
                    <div class="ref">${refText}</div>
                </div>
                <div class="overlay-blur" id="fullscreen-overlay">
                    <div class="overlay-buttons">
                        <button class="fullscreen-btn" id="fullscreen-btn">Enter Full Screen</button>
                        <button class="close-x-btn" id="close-x-btn" title="Close Overlay">&#10005;</button>
                    </div>
                </div>
                <script>
                    document.getElementById('fullscreen-btn').addEventListener('click', function() {
                        if (document.documentElement.requestFullscreen) {
                            document.documentElement.requestFullscreen();
                        }
                        document.getElementById('fullscreen-overlay').style.display = 'none';
                        // Remove cursor hiding here
                    });

                    document.getElementById('close-x-btn').addEventListener('click', function() {
                        document.getElementById('fullscreen-overlay').style.display = 'none';
                        document.body.style.cursor = 'auto';
                    });

                    document.addEventListener('fullscreenchange', function() {
                        if (!document.fullscreenElement) {
                            // Fullscreen exited, show overlay and cursor
                            document.getElementById('fullscreen-overlay').style.display = 'flex';
                            document.body.style.cursor = 'auto';
                        } else {
                            // Hide cursor only in fullscreen mode
                            document.body.style.cursor = 'none';
                        }
                    });

                    // Always show cursor when overlay is visible
                    const observer = new MutationObserver(function() {
                        const overlay = document.getElementById('fullscreen-overlay');
                        if (overlay && overlay.style.display !== 'none') {
                            document.body.style.cursor = 'auto';
                        }
                    });
                    observer.observe(document.body, { attributes: true, childList: true, subtree: true });

                    // Add F key shortcut for fullscreen and exit fullscreen
                    document.addEventListener('keydown', function(e) {
                        if (e.key === 'f' || e.key === 'F') {
                            if (document.fullscreenElement) {
                                // If already in fullscreen, exit fullscreen
                                if (document.exitFullscreen) {
                                    document.exitFullscreen();
                                }
                            } else {
                                // Not in fullscreen, enter fullscreen
                                if (document.documentElement.requestFullscreen) {
                                    document.documentElement.requestFullscreen();
                                }
                                document.getElementById('fullscreen-overlay').style.display = 'none';
                                // Remove cursor hiding here
                            }
                        }
                    });
                </script>
            </body>
            </html>
        `);
        win.document.close();
    }
});
