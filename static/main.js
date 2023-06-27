$( function() {
    $( "#sortable" ).sortable({handle: 'header'});
} );

// If the user clicks Save, then send the notes to /savenotes, disable the text area, then replace the notes with the response
$('#save_notes').on('click', function(e) {
    e.preventDefault();
    var notes = $('#notes').val();
    $('#notes').prop('disabled', true);
    $('#save_notes').prop('disabled', true);
    $('#notes').css('background-color', '#ccc');
    $.post('/savenotes', { 
        notes: notes
    }, function(response) {
        let r = JSON.parse(response);
        $('#notes_most_recent').html(r[0]);
        $('#notes').prop('disabled', false);
        $('#save_notes').prop('disabled', false);
        $('#notes').css('background-color', '#fff');
        $('#notes').val('');
    });
});

// ChatBot Functionality
$('#chat-form').on('submit', function(e) {
    e.preventDefault();
    var question = $('#question').val();
    $('#chatbox').append('<div>You: ' + question + '</div>');

    div_response = $('<div class="chatmessage bot">');
    div_response.html('Loading...')
    $('#chatbox').append(div_response);
    $('#chatbox').scrollTop($('#chatbox')[0].scrollHeight);

    $('#question').val('');
    var checkedValues = [];
    $('#chat-form input[type="checkbox"]:checked').each((input) => {
        checkedValues.push($('#chat-form input[type="checkbox"]:checked')[input].name);
    })
    $('#chatbox').scrollTop($('#chatbox')[0].scrollHeight);
    $.post('/ask', { 
        question: question,
        modules: checkedValues.join(','),
        temperature: $('#temp').val()
    }, function(response) {
        let r = JSON.parse(response);
        r_formatted = r;
        let chat_response = r[0];
        let source = r[1];
        let nouns = r[2];

        // Iterate over the array of nouns, and replace instances of those words in the chat response with links to the NPC
        nouns.forEach((noun) => {
            let regex = new RegExp(noun, 'gi');
            chat_response = chat_response.replace(regex, `<span class="chat_name" onmouseover="show_chat_options('${noun}', this)" onmouseout="hide_chat_options(this)">${noun}</span>`);
        })

        console.log(r_formatted)
        div_r1 = $(`<div>AI: ${chat_response}</div><div><small><ul><li>${source}</li></ul></small></div>`);
        div_response.html(div_r1);
        $('#chatbox').scrollTop($('#chatbox')[0].scrollHeight);
    }).fail(function(jqXHR, textStatus, errorThrown) {
        div_response.html('An error occurred, please try again - ' + errorThrown);
    });        
});

// When the game select changes to a value, send a request to /setgame to set the game
$('#game').on('change', function(e) {
    e.preventDefault();
    var game = $('#game').val();
    $('#notes_most_recent').html("<div></div><div></div><div></div>");
    $('#notes_most_recent').addClass('lds-ring')
    $('#notes').val('');
    $('#game').prop('disabled', true);
    $('#notes').prop('disabled', true);
    $('#save_notes').prop('disabled', true);
    $('#notes').css('background-color', '#ccc');
    
    $.post('/setgame', { 
        game: game
    }, function(response) {
        $('#notes_most_recent').html(JSON.parse(response)[0])
        let notes_files = JSON.parse(response)[1];
        let names = JSON.parse(response)[2];
        let game_names = JSON.parse(response)[3];
        $('#game').prop('disabled', false);
        $('#notes').prop('disabled', false);
        $('#save_notes').prop('disabled', false);
        $('#notes').css('background-color', '#fff');
        $('#notes_most_recent').removeClass('lds-ring')
        $('#previous_notes_list').html('');
        notes_files.forEach((file) => {
            $('#previous_notes_list').append('<div id="note_'+file+'"><a href="javascript:show_note(\''+file+'\')">' + file + '</a></div>');
        })

        $('#names').html(
            `<table id="table_names">
                <tr>
                    <th>Name</th><th>Quick Gen</th><th>Generated</th><th>Add to Game</th><th>Delete</th>
                </tr>`
        );
        names.forEach((row)=> {
            let id = row.id;
            let name = row.name;
            let npc_class = row.npc_class;
            let file_icon = (row.background) ? 'fa fa-file' : 'fa fa-file-o';
            $('#table_names').append(
                `<tr id="name_${id}">
                <td><a href="javascript:show_name('${id}', '${name}')">${name}</a></td>
                <td id="quick_gen_${id}" class="center">`+
                    ((row.background) ? '' : `<small><a href="javascript:show_name('${id}', '${name}', 1)">&gt;&gt;</a></small>`)
                +`</td><td class="center">
                    <i id="file_icon_${id}"  class="${file_icon}"></i>
                </td>
                <td class="center">
                    <a href="javascript:add_name('${id}', '${row.background}', '${name}')">+</a>
                </td>
                <td class="center">
                    <a href="javascript:delete_name('${id}')">X</a>
                </td>
                </tr>`
            );
        })
        $('#names').append('</table>');

        if (game_names.length > 0) {
            $('#game_names').html(
                `<table id="table_game_names">
                    <tr>
                        <th>Name</th><th>Quick Gen</th><th>Generated</th><th>Delete</th>
                    </tr>`
            );
            game_names.forEach((row)=> {
                let id = row.id;
                let name = row.name;
                let npc_class = row.npc_class;
                let file_icon = (row.background) ? 'fa fa-file' : 'fa fa-file-o';
                $('#table_game_names').append(
                    `<tr id="game_name_${id}">
                    <td><a href="javascript:show_name('${id}', '${name}')">${name}</a></td>
                    <td id="game_quick_gen_${id}" class="center">`+
                        ((row.background) ? '' : `<small><a href="javascript:show_name('${id}', '${name}', 1)">&gt;&gt;</a></small>`)
                    +`</td><td class="center">
                        <i id="game_file_icon_${id}"  class="${file_icon}"></i>
                    </td>
                    <td class="center">
                        <a href="javascript:delete_name('${id}')">X</a>
                    </td>
                    </tr>`
                );
            })
            $('#game_names').append('</table>');
        } else {
            $('#game_names').html('No NPCs have been created for this game yet, click the + buton to add a pregenerated NPC to this game, or click <a href="javascript:create_npc()">+ Add NPC</a> to create a new NPC for this game');
        }
    });
});

// Chat Bot Collapsible Sections
var coll = document.getElementsByClassName("collapsible");
var i;
for (i = 0; i < coll.length; i++) {
    coll[i].addEventListener("click", function() {
        this.classList.toggle("active");
        var content = this.nextElementSibling;
        if (content.style.display === "block") {
            content.style.display = "none";
        } else {
            content.style.display = "block";
        }
    });
}

// Clicking on the "All" checkbox checks all the other checkboxes
$('#Core').on('click', function(e) {
    $('#PlayersHandbook').prop('checked', $('#Core').prop('checked'));
    $('#DungeonMastersGuide').prop('checked', $('#Core').prop('checked'));
    $('#MonsterManual').prop('checked', $('#Core').prop('checked'));
    $('#Core').prop('checked', $('#Core').prop('checked'));
})

$('#Adventures').on('click', function(e) {
    $('#lmop').prop('checked', $('#Adventures').prop('checked'));
    ['lmop', 'hotdq', 'rot', 'pota', 'oota', 'cos', 'skt', 'tftyp', 'toa', 'wdh', 'wdotmm', 'gos', 'bgdia', 'idrotf', 'cm', 'twbtw', 'rrakkma', 'llok', 'hftr', 'doip', 'slw', 'sdw', 'dc', 'imr', 'fs', 'cotn', 'trc', 'jttrc', 'sa', 'dosi', 'dsotdq', 'p13', 'kftgv'].forEach((adventure) => {
        $('#' + adventure).prop('checked', $('#Adventures').prop('checked'));
    })
})

$('#Supplements').on('click', function(e) {
    ['vgm', 'mtf', 'xge', 'ggtr', 'erftlw', 'egtw', 'mot', 'tce', 'vrgr', 'ftd', 'slox', 'sbaa', 'saag', 'mpmotm', 'scag', 'ttp', 'oga', 'wgte', 'ai', 'lr', 'mffv1', 'saccoc', 'mcav1', 'tvd', 'mcav2', 'tg', 'legendary', 'lmi', 'misplaced'].forEach((supplement) => {
        $('#' + supplement).prop('checked', $('#Supplements').prop('checked'));
    })
})

$('#3rdParty').on('click', function(e) {
    ['dotn'].forEach((thirdParty) => {
        $('#' + thirdParty).prop('checked', $('#3rdParty').prop('checked'));
    })
})

function show_note(date) {
    console.log('note_'+date)
    var div = $('#note_'+date);
    div.html("<div></div><div></div><div></div>");
    div.addClass('lds-ring')
    $.post('/getnote', { 
        date: date
    }, function(response) {
        let r = JSON.parse(response)[0];
        r = r.replace(/(END OF)?.*?SESSION NOTES FOR \w+\n*/g, '');
        r = r.replace(/\n/g, '<br/>');
        console.log(r);
        div.html($.parseHTML(r))
        div.removeClass('lds-ring')
        div.addClass('date-focused');
        // Add a close button, that goes back to the previous value
        div.append('<button type="button" onclick="close_note(\''+date+'\')">Close</button>')
    });
}

function close_note(date) {
    var div = $('#note_'+date);
    div.removeClass('date-focused');
    div.html('<a href="javascript:show_note(\''+date+'\')">' + date + '</a>');
}

function create_npc() {
    var modal = document.getElementById("modal");
    var span = document.getElementsByClassName("close")[0];
    modal.style.display = "block";

    var div = $('#modal_content');
    $('#modal-header').html('Create NPC')
    let html = "<div><i>Tell me what you know about your NPC. I'll tell you the rest...</i></div>";
    html += "<form id='create_npc_form' method='post'>";
    html += "<table>";
    html += '<tr><td><label>Name:</label></td><td><input type="text" id="npc_name" name="npc_name"></td></td>';
    html += '<tr><td><label>Class:</label></td><td><input type="text" id="npc_class" name="npc_class"></td></td>';
    html += '<tr><td><label>Background:</label></td><td><input type="text" id="npc_background" name="npc_background"></td></td>';
    html += '<tr><td><label>Alignment:</label></td><td><input type="text" id="npc_alignment" name="npc_alignment"></td></td>';
    html += '<tr><td><label>Gender:</label></td><td><input type="text" id="npc_gender" name="npc_gender"></td></td>';
    html += '<tr><td><label>Age:</label></td><td><input type="text" id="npc_age" name="npc_age"></td></td>';
    html += '<tr><td><label>Height:</label></td><td><input type="text" id="npc_height" name="npc_height"></td></td>';
    html += '<tr><td><label>Weight:</label></td><td><input type="text" id="npc_weight" name="npc_weight"></td></td>';
    html += '<tr><td><label>Eye Color:</label></td><td><input type="text" id="npc_eye_color" name="npc_eye_color"></td></td>';
    html += '<tr><td><label>Eye Description:</label></td><td><input type="text" id="npc_eye_description" name="npc_eye_description"></td></td>';
    html += '<tr><td><label>Hair Color:</label></td><td><input type="text" id="npc_hair_color" name="npc_hair_color"></td></td>';
    html += '<tr><td><label>Hair Style:</label></td><td><input type="text" id="npc_hair_style" name="npc_hair_style"></td></td>';
    html += '<tr><td><label>Ears:</label></td><td><input type="text" id="npc_hair_ears" name="npc_ears"></td></td>';
    html += '<tr><td><label>Nose:</label></td><td><input type="text" id="npc_nose" name="npc_nose"></td></td>';
    html += '<tr><td><label>Mouth:</label></td><td><input type="text" id="npc_mouth" name="npc_mouth"></td></td>';
    html += '<tr><td><label>Chin:</label></td><td><input type="text" id="npc_chin" name="npc_chin"></td></td>';
    html += '<tr><td><label>Features:</label></td><td><input type="text" id="npc_features" name="npc_features"></td></td>';
    html += '<tr><td><label>Flaws:</label></td><td><input type="text" id="npc_flaws" name="npc_flaws"></td></td>';
    html += '<tr><td><label>Ideals:</label></td><td><input type="text" id="npc_ideals" name="npc_ideals"></td></td>';
    html += '<tr><td><label>Bonds:</label></td><td><input type="text" id="npc_bonds" name="npc_bonds"></td></td>';
    html += '<tr><td><label>Personality:</label></td><td><input type="text" id="npc_personality" name="npc_personality"></td></td>';
    html += '<tr><td><label>Mannerism:</label></td><td><input type="text" id="npc_mannerism" name="npc_mannerism"></td></td>';
    html += '<tr><td><label>Talent:</label></td><td><input type="text" id="npc_talent" name="npc_talent"></td></td>';
    html += '<tr><td><label>Ability:</label></td><td><input type="text" id="npc_ability" name="npc_ability"></td></td>';
    html += '<tr><td><label>Skill:</label></td><td><input type="text" id="npc_skill" name="npc_skill"></td></td>';
    html += '<tr><td><label>Language:</label></td><td><input type="text" id="npc_language" name="npc_language"></td></td>';
    html += '<tr><td><label>Inventory:</label></td><td><input type="text" id="npc_inventory" name="npc_inventory"></td></td>';
    html += '<tr><td><label>Body:</label></td><td><input type="text" id="npc_body" name="npc_body"></td></td>';
    html += '<tr><td><label>Clothing:</label></td><td><input type="text" id="npc_clothing" name="npc_clothing"></td></td>';
    html += '<tr><td><label>Hands:</label></td><td><input type="text" id="npc_hands" name="npc_hands"></td></td>';
    html += '<tr><td><label>Jewelry:</label></td><td><input type="text" id="npc_jewelry" name="npc_jewelry"></td></td>';
    html += '<tr><td><label>Voice:</label></td><td><input type="text" id="npc_voice" name="npc_voice"></td></td>';
    html += '<tr><td><label>Attitude:</label></td><td><input type="text" id="npc_attitude" name="npc_attitude"></td></td>';
    html += '<tr><td><label>Deity:</label></td><td><input type="text" id="npc_deity" name="npc_deity"></td></td>';
    html += '<tr><td><label>Occupation:</label></td><td><input type="text" id="npc_occupation" name="npc_occupation"></td></td>';
    html += '<tr><td><label>Wealth:</label></td><td><input type="text" id="npc_wealth" name="npc_wealth"></td></td>';
    html += '<tr><td><label>Family:</label></td><td><input type="text" id="npc_family" name="npc_family"></td></td>';
    html += '<tr><td><label>Faith:</label></td><td><input type="text" id="npc_faith" name="npc_faith"></td></td>';
    html += '</table>';
    html += '<div><input type="button" value="Create" onclick="create_npc_submit()"></div>';
    html += "</form>"
    div.html(html)
}

function create_npc_submit() {
    // Get all the values from the form
    var form = $('#create_npc_form');
    var data = form.serializeArray();
    var div = $('#modal_content');
    $.post('/createnpc', {
        data: data
    }, function(response) {
        let r = JSON.parse(response);
        console.log(r);
        // r is a hash, iterate through it and display it
        let html = '<table class="npc_details">';
        let id = r['id'];
        Object.keys(r).forEach((key) => {
            if (key == 'summary' || key == 'id') {
                return;
            }
            let k = key
            // Capitalize the first letter of key
            key = key.charAt(0).toUpperCase() + key.slice(1);
            // replace _ with a space
            key = key.replace(/_/g, ' ');
            html += '<tr class="npc"><td nowrap>' + key + `</td><td id="${id}_${k}">` + r[k] + `</td><td><img src="/static/img/arrow-rotate-right-solid.svg"/ class="regen" onclick="regen_key(${id}, '${k}', this)"></td></tr>`;
        })           
        html += '</table>';     
        html += `<div class="npc_summary">
            <div class="regen" title="Regenerate Summary" onclick="regen_summary('${id}')"></div>
            <div id="npc_summary">${r['summary']}</div>
            </div>`;
        html += '<div style="clear:both"></div>';
        div.html(html)

        $('#table_names').append(
                `<tr id="name_${id}">
                <td><a href="javascript:show_name('${id}', '${r['name']}')">${r['name']}</a></td>
                <td></td>
                <td>
                    <i id="file_icon_${id}"  class="fa fa-file"></i>
                </td><td>
                    <a href="javascript:delete_name('${id}')">X</a>
                </td>
                </tr>`
            );


        $("#file_icon_"+id).removeClass('fa-file-o');
        $("#file_icon_"+id).addClass('fa-file');
        $("#quick_gen_"+id).html('')

        // Add a close button, that goes back to the previous value
        div.append('<button type="button" onclick="close_name(\''+id+'\')">Close</button>')
    })
}

function show_name (id=null, name=null, quick=0) {
    console.log(id)
    var modal = document.getElementById("modal");
    var span = document.getElementsByClassName("close")[0];
    modal.style.display = "block";

    var div = $('#modal_content');
    $('#modal-header').html(name)
    div.html("Loading...");
    div.addClass('lds-ring')
    $.post('/getnpc', { 
        id: id,
        name: name,
        quick: quick
    }, function(response) {
        let r = JSON.parse(response);
        console.log(r);
        if (id == null)
            id = r['id'];
        // r is a hash, iterate through it and display it
        let npc_img_html = (r['image_exists'])
            ? `<img src="/static/img/npc/${id}.png" class="npc_image"/>`
            : '<a href="javascript:gen_npc_image(\''+id+'\')">Generate Image</a>';
        let html = '<table class="npc_details">';
        Object.keys(r).forEach((key) => {
            if (key == 'summary' || key == "id" || key == "image_exists" || key == "game_id") {
                return;
            }
            let k = key
            // Capitalize the first letter of key
            key = key.charAt(0).toUpperCase() + key.slice(1);
            // replace _ with a space
            key = key.replace(/_/g, ' ');
            html += '<tr class="npc"><td nowrap>' + key + `</td><td id="${id}_${k}">` + r[k] + `</td><td><img src="/static/img/arrow-rotate-right-solid.svg"/ class="regen" onclick="regen_key(${id}, '${k}', this)"></td></tr>`;
        })           
        html += '</table>';     
        html += `<div class="npc_summary">
            <div class="regen" title="Regenerate Summary" onclick="regen_summary('${id}')"></div>
            <div id="npc_summary">${r['summary']}</div>
            </div>`;
        html += `<div class="npc_image">${npc_img_html}</div>`;
        html += '<div style="clear:both"></div>';
        div.html(html)
        div.removeClass('lds-ring')
    });
}

function delete_name(id) {
    $.post('/deletename', { 
        id: id
    }, function(response) {
        if ($('#name_'+id))
            $('#name_'+id).remove();
        if ($('#game_name_'+id))
        $('#game_name_'+id).remove();
    });
}

function add_name(id, background, name) {
    $.post('/addname', { 
        id: id
    }, function(response) {
        tr = $('#name_'+id);
        tr.remove();  
        let file_icon = (background) ? 'fa fa-file' : 'fa fa-file-o';
        tr = `<tr>
            <td><a href="javascript:show_name('${id}','${name}')">${name}</a></td>
            <td id="game_quick_gen_${id}" class="center">`+
                ((background) ? '' : `<small><a href="javascript:show_name('${id}', '${name}', 1)">&gt;&gt;</a></small>`)
            +`</td><td class="center">
                <i id="game_file_icon_${id}"  class="${file_icon}"></i>
            </td>
            <td><a href="javascript:delete_name('${id}')">X</a></td>
            </tr>`
        $('#table_game_names').append(tr);
    });
}

function close_name() {
    var modal = document.getElementById("modal");
    modal.style.display = "none";
}

window.onclick = function(event) {
    var modal = document.getElementById("modal");
    if (event.target == modal) {
        close_modal();
    }
}

function close_modal() {
    var modal = document.getElementById("modal");
    modal.style.display = "none";
}

function regen_summary(id) {
    var div = $('#npc_summary');

    div.css('display', 'none');
    div.html("Loading...");
    div.addClass('lds-ring')
    $.post('/regensummary', { 
        id: id
    }, function(response) {
        div.html(response)
        div.removeClass('lds-ring')
        div.css('display', 'block');
    });
}

function regen_key(id, key, img) {
    let td = $('#'+id+'_'+key);
    img.classList.add('spin');
    $.post('/regenkey', { 
        id: id,
        key: key
    }, function(response) {
        td.html(response);
        img.classList.remove('spin');
    });
}

function gen_npc_image(id) {
    $.post('/gennpcimage', { 
        id: id
    }, function(response) {
        let div = $('.npc_image');
        div.html('<img src="/static/img/npc/'+id+'.png" class="npc_image"/>');
    });
}

function show_chat_options(name, span) {
    // Create chat_options div
    let div = $('<div class="chat_option">');
    div.html('View NPC');
    div.addClass('chat_options');
    $(span).append(div);
    // Get the height of the span
    let height = $(span).height();
    div.css('top', height-5);
    div.css('display', 'block');

    // Add a click handler to the div
    div.on('click', function(e) {
        e.preventDefault();
        hide_chat_options(span, true);
        show_name(null, span.innerHTML, false);
    })
}

function hide_chat_options(span, force=false) {
    if (!force) {
        // Determine which divs the mouse is over
        let divs = document.elementsFromPoint(event.clientX, event.clientY);
        let found = false;
        divs.forEach((div) => {
            if (div.classList.contains('chat_options')) {
                found = true;
            }
        })
        
        if (!found)
            $(span).find('.chat_options').remove();
    }
    else {
        $(span).find('.chat_options').remove();
    }
}

function toggle_visibility(id) {
    var e = document.getElementById(id);
    if (e.style.display == 'block')
        e.style.display = 'none';
    else
        e.style.display = 'block';
}
