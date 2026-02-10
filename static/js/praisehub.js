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
