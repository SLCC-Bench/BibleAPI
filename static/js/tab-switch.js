$(function() {
    function activateTab(tab) {
        $('#tab-scriptures').removeClass('border-b-2 border-blue-600 text-black').addClass('text-gray-500');
        $('#tab-songs').removeClass('border-b-2 border-blue-600 text-black').addClass('text-gray-500');
        $('#tab-media').removeClass('border-b-2 border-blue-600 text-black').addClass('text-gray-500');
        $('#scripture-table').hide();
        $('#songs-tab-content').hide();
        $('#sidebar-translation').hide();
        $('#sidebar-reference').hide();
        $('#sidebar-song-search').hide();
        $('#sidebar-media-tabs').hide();
        $('#sidebar-book-suggestions').hide();

        if(tab === 'scriptures') {
            $('#tab-scriptures').addClass('border-b-2 border-blue-600 text-black').removeClass('text-gray-500');
            $('#scripture-table').show();
            $('#sidebar-translation').show();
            $('#sidebar-reference').show();
            $('#sidebar-book-suggestions').show();
        } else if(tab === 'songs') {
            $('#tab-songs').addClass('border-b-2 border-blue-600 text-black').removeClass('text-gray-500');
            $('#songs-tab-content').show();
            $('#sidebar-song-search').show();
            $('#sidebar-book-suggestions').hide();
        } else if(tab === 'media') {
            $('#tab-media').addClass('border-b-2 border-blue-600 text-black').removeClass('text-gray-500');
            $('#sidebar-media-tabs').show();
            $('#sidebar-book-suggestions').hide();
            // Default to Image tab
            activateMediaTab('image');
        }
    }

    function activateMediaTab(mediaTab) {
        $('#media-tab-image').removeClass('border-b-2 border-blue-600 text-black').addClass('text-gray-500');
        $('#media-tab-video').removeClass('border-b-2 border-blue-600 text-black').addClass('text-gray-500');
        $('#media-tab-presentation').removeClass('border-b-2 border-blue-600 text-black').addClass('text-gray-500');
        $('#media-image-content').hide();
        $('#media-video-content').hide();
        $('#media-presentation-content').hide();

        if(mediaTab === 'image') {
            $('#media-tab-image').addClass('border-b-2 border-blue-600 text-black').removeClass('text-gray-500');
            $('#media-image-content').show();
        } else if(mediaTab === 'video') {
            $('#media-tab-video').addClass('border-b-2 border-blue-600 text-black').removeClass('text-gray-500');
            $('#media-video-content').show();
        } else if(mediaTab === 'presentation') {
            $('#media-tab-presentation').addClass('border-b-2 border-blue-600 text-black').removeClass('text-gray-500');
            $('#media-presentation-content').show();
        }
    }

    activateTab('scriptures');
    $('#tab-scriptures').on('click', function() { activateTab('scriptures'); });
    $('#tab-songs').on('click', function() { activateTab('songs'); });
    $('#tab-media').on('click', function() { activateTab('media'); });

    $('#media-tab-image').on('click', function() { activateMediaTab('image'); });
    $('#media-tab-video').on('click', function() { activateMediaTab('video'); });
    $('#media-tab-presentation').on('click', function() { activateMediaTab('presentation'); });
});
