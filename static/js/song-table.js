$(function() {
    // Replace static table with Tabulator
    var songTable = new Tabulator("#songs-table", {
        layout: "fitColumns",
        height: "300px",
        columns: [
            { title: "Title", field: "title", headerSort: false },
            { title: "Author", field: "author", headerSort: false },
            { title: "Album", field: "album", headerSort: false }
        ],
        data: [], // Start empty, populate as needed
        placeholder: "No songs loaded. Search to add songs."
    });

    // Example: Add a song (call this from elsewhere)
    window.addSong = function(song) {
        songTable.addRow(song);
    };

    // Example: Clear all songs
    window.clearSongs = function() {
        songTable.clearData();
    };

    // Example: Set all songs
    window.setSongs = function(songs) {
        songTable.replaceData(songs);
    };

    // Optionally, expose songTable for advanced manipulation
    window.songTable = songTable;
});
