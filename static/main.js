$( function() {
    $( "#sortable" ).sortable({handle: 'header'});
    $('#reminder_list').sortable();
} );

// If the user clicks Save, then send the notes to /savenotes, disable the text area, then replace the notes with the response
$('#save_notes').on('click', function(e) {
    e.preventDefault();
    var notes = $('#notes').val();
    $('#notes').prop('disabled', true);
    $('#save_notes').prop('disabled', true);
    $('#notes').css('background-color', '#ccc');
    $.post('/savenotes', { 
        notes: notes,
        game_id: $('#game').val()
    }, function(response) {
        let r = JSON.parse(response);
        $('#notes_most_recent').html(r[0]);
        $('#notes').prop('disabled', false);
        $('#save_notes').prop('disabled', false);
        $('#notes').css('background-color', '#fff');
        $('#notes').val('');
        refresh_notes_list();
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
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
        game_id: $('#game').val()
    }, function(response) {
        let r = JSON.parse(response);
        r_formatted = r;
        let chat_response = r["answer"];
        let source = r["source"];
        let nouns = r["people"];

        // Iterate over the array of nouns, and replace instances of those words in the chat response with links to the NPC
        nouns.forEach((noun) => {
            let regex = new RegExp(noun, 'gi');
            chat_response = chat_response.replace(regex, `<span class="chat_name" onmouseover="show_chat_options('${noun}', this)" onmouseout="hide_chat_options(this)">${noun}</span>`);
        })
        chat_response.replace(/\n/g, "<br/>\n");

        console.log(r_formatted)
        div_r1 = $(`<div>AI: ${chat_response}</div><div><small><ul><li>Source: ${source}</li></ul></small></div>`);

        div_response.html(div_r1);
        $('#chatbox').scrollTop($('#chatbox')[0].scrollHeight);

        if (r["frontend"]) {
            for (let i = 0; i < r["frontend"].length; i++) {
                switch (r["frontend"][i]) {
                    case "refresh_npc_list":
                        // Refresh the list of NPCs
                        refresh_npc_list();
                    case "refresh_reminders":
                        // Refresh Reminders
                        refresh_reminders();
                }
            }
        }
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

    if (game == 0) { // Create a new game
        modal.style.display = "block";
        var div = $('#modal_content');
        $('#modal-header').html('Create Game')
        let html = "<div><i>What would you like to name your game?</i></div>";
        html += "<form id='create_game_form' method='post'>";
        html += "<table>";
        html += '<tr><td><label>Name:</label></td><td><input type="text" id="game_name" name="game_name"></td></td>';
        html += '<tr><td><label>Abbreviation:</label></td><td><input type="text" id="abbr" name="abbr"></td></td>';
        html += "</table>"
        html += '<div><input type="button" value="Create" onclick="create_game_submit()"></div>';
        html += "</form>"
        div.html(html)        
    } else { // Load the game
        $.post('/setgame', { 
            game_id: game
        }, function(response) {
            $('#notes_most_recent').html(JSON.parse(response)[0])
            json = JSON.parse(response);
            let notes_files = json[1];
            let game_names = json[2];
            let plot_points = json[3];
            let reminders = json[4];
            $('#game').prop('disabled', false);
            $('#notes').prop('disabled', false);
            $('#save_notes').prop('disabled', false);
            $('#notes').css('background-color', '#fff');
            $('#notes_most_recent').removeClass('lds-ring')
            $('#previous_notes_list').html('');
            notes_files.forEach((note) => {
                console.log(note)
                $('#previous_notes_list').append('<div id="note_'+note['date']+'"><a href="javascript:show_note(\''+note['date']+'\', \''+note['id']+'\')">' + note['date'] + '</a></div>');
            })
    
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
    
            $('#plot_points').html('');
            for (let i = 0; i < plot_points.length; i++) {
                let plot_point = plot_points[i];
                let div = $('<div class="plot_point">');
                let title = $('<div class="plot_point_title">');
                title.html(plot_point.title);
                div.append(title);
                div.draggable({containment: "parent"});
                div.droppable({
                    over: function(event, ui) {
                        $(this).addClass('plot_point_hover');
                    },
                    out: function(event, ui) {
                        $(this).removeClass('plot_point_hover');
                    }
                })
                $('#plot_points').append(div);
            }
            
            $('#reminder_list').html('')
            for (let i = 0; i < reminders.length; i++) {
                let reminder = reminders[i];
                console.log(reminder)
                let div = $('<div class="reminder">');
                let title = $('<div class="reminder_title">');
                let delete_ = $('<div class="reminder_delete" onclick="delete_reminder('+reminder.id+')">');
                delete_.html('X');
                title.html(reminder.title);
                div.append(delete_);
                div.append(title);
                $('#reminder_list').append(div);
            };
    
            $('#audio_status').html('');
            // Add mp3 upload
            $('#audio_status').append('<div>Upload MP3 of a Session to create notes, and make them searchable by the chatbot</div><br/><br/>')
            $('#audio_status').append('<label for="audio_file">Upload Audio File:</label>');
            $('#audio_status').append('<input type="file" id="audio_file" name="audio_file" accept="audio/mp3">');
            $('#audio_status').append('<input type="button" id="audio_upload" value="Upload">');
            $('#audio_status').append('<div id="audio_progress"></div>');
            $('#audio_upload').on('click', function(e) {
                e.preventDefault();
                $('#audio_upload').prop('disabled', true);
                var file = $('#audio_file').prop('files')[0];
                var formData = new FormData();
                formData.append('audio_file', file);
                formData.append('game_id', $('#game').val());
                $.ajax({
                    url: '/uploadaudio',
                    data: formData,
                    processData: false,
                    contentType: false,
                    type: 'POST',
                    success: function(data){
                        json = JSON.parse(data);
                        var task_id;
                        var div_progress = $('<div class="audio_progress">');
                        if (json[0]['error']) {
                            div_progress.html('Error: ' + json[0]['error']);
                            $('#audio_upload').prop('disabled', false);
                        } else {
                            div_progress.html('Queued: ' + file.name);
                            task_id = json[0];
                        }
                        $('#audio_status').append(div_progress);
    
                        var intervalId = setInterval(function() {
                            $.ajax({
                                url: '/getaudiostatus',
                                data: {
                                    task_id: task_id
                                },
                                type: 'POST',
                                success: function(data){
                                    json = JSON.parse(data);
                                    if (json['error']) {
                                        div_progress.html('Error: ' + json['error']);
                                        $('#audio_upload').prop('disabled', false);
                                        clearInterval(intervalId);
                                    } else if (json[0] == 'Complete') {
                                        div_progress.html('Complete');
                                        clearInterval(intervalId);
                                        $('#audio_upload').prop('disabled', false);
                                        refresh_notes_list();
                                    } else {
                                        div_progress.html(json[1]);
                                    }
                                },
                                error: function(data) {
                                    div_progress.html('Error: ' + data);
                                    $('#audio_upload').prop('disabled', false);
                                }
                            });
                        }, 5000);
                    }
                });
            })
        }).fail(function(jqXHR, textStatus, errorThrown) {
            alert('An error occurred, please try again - ' + errorThrown)
            document.location.reload();
        });
    }
    
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

function create_game_submit() {
    var form = $('#create_game_form');
    var data = form.serializeArray();
    params = {};
    data.forEach((d) => {
        params[d.name] = d.value;
    })
    $.post('/creategame',
    params,
    function(response) {
        let r = JSON.parse(response);
        $('#game').append('<option value="' + r['id'] + '">' + r['name'] + '</option>');
        $('#game').val(r['id']);
        $('#modal').css('display', 'none');
        document.location = '/home'
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    })
}

function refresh_npc_list() {
    $.post('/getnpcs', {
        game_id: $('#game').val()
    }, function(response) {
        let r = JSON.parse(response);
        $('#names').html(
            `<table id="table_names">
                <tr>
                    <th>Name</th><th>Quick Gen</th><th>Generated</th><th>Add to Game</th><th>Delete</th>
                </tr>`
        );
        r.forEach((row)=> {
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
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    });
}

function show_note(date, note_id) {
    console.log('show_note()')
    $.post('/getnote', { 
        id: note_id,
        game_id: $('#game').val()
    }, function(response) {
        let r = JSON.parse(response)[0];
        r = r.replace(/(END OF)?.*?SESSION NOTES FOR \w+\n*/g, '');
        r = r.replace(/\n/g, '<br/>');

        modal.style.display = "block";
        var div = $('#modal_content');
        // Use Date to get the date in Month Day, Year format
        let date_formatted = new Date(date + "T00:00");
        date_formatted = date_formatted.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
        $('#modal-header').html("Session Notes: <span id='session_date'>" + date_formatted + "</span>")
        let html = '<div class="note">' + r + '</div>';
        div.html(html)

        div_btns = $('#modal-buttons');
        btn_edit = $('<span id="modal-edit" class="modal-button">');
        btn_edit.html('[Edit]')
        btn_edit.on('click', function() { edit_note (note_id, date) });
        btn_delete = $('<span id="modal-delete" class="modal-button">');
        btn_delete.html('[Delete]')
        btn_delete.on('click', function() { delete_note (date) });
        div_btns.append(btn_edit);
        div_btns.append(btn_delete);
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown)
    });
}

function edit_note (id, date) {
    console.log('edit_note()')
    txt = $('#modal_content').html();
    txt = txt.replace(/<br>/g, '\n');
    txt = txt.replace(/<div.*?>/g, '');
    txt = txt.replace(/<\/div>/g, '');

    textarea = $('<textarea id="modal_textarea">');
    textarea.val(txt);
    $('#modal_content').html(textarea);
    $('#modal-edit').off()
    btn_save = $('<span id="modal-edit" class="modal-button">');
    btn_save.html('[Save]')
    btn_save.on('click', function() { save_note (date, textarea) });
    $('#modal-buttons').append(btn_save);
    $('#modal-edit').remove()

    sesison_date = $('#session_date')
    sesison_date.html('<input type="date" id="session_date_input" value="' + date + '">')
    $('#session_date_input').on('change', function() {
        new_date = $('#session_date_input').val()
        $.post('/update_notes_date', {
            id: id,
            new_date: new_date
        }, function(response) {
            console.log(response)
            $('#note_'+date).html('<a href="javascript:show_note(\''+new_date+'\', \''+id+'\')">' + new_date + '</a>')
        }).fail(function(jqXHR, textStatus, errorThrown) {
            alert('An error occurred, please try again - ' + errorThrown);
        });
    });
}

function save_note(date, textarea) {
    console.log('save_note()')
    console.log(date)
    txt = textarea.val();
    console.log(txt)
    $.post('/updatenote', { 
        date: date,
        note: txt,
        game_id: $('#game').val()
    }, function(response) {
        modal.style.display = "none";
        $('#modal-buttons').html('')
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    });
}

function delete_note (date) {
    if (confirm("Are you sure you want to delete this note?") == false) {
        return;
    }
    $.post('/deletenote', {
        date: date,
        game_id: $('#game').val()
    }, function(response) {
        $('#note_'+date).remove();
        modal.style.display = "none";
        $('#modal-buttons').html('')
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    });
}

function create_npc() {
    var modal = document.getElementById("modal");
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
    params = {
        game_id: $('#game').val()
    };
    data.forEach((d) => {
        params[d.name] = d.value;
    })
    var div = $('#modal_content');
    $.post('/createnpc',
    params,
    function(response) {
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
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    })
}

function create_plot_point() {
    var modal = document.getElementById("modal");
    modal.style.display = "block";
    var div = $('#modal_content');
    $('#modal-header').html('Create Plot Point')
    let html = "<form id='create_npc_form' method='post'>";
    html += "<table>";
    html += '<tr><td><label>Title:</label></td><td><input type="text" id="plot_point_title" name="plot_point_title"></td></td>';
    html += '<tr><td><label>Summary:</label></td><td><textarea id="plot_point_summary" name="plot_point_summary"></textarea></td></td>';
    html += '</table>';
    html += '<div><input type="button" value="Create" onclick="create_plot_point_submit()"></div>';
    html += "</form>"
    div.html(html)
}

function create_plot_point_submit() {
    // Get all the values from the form
    var modal = document.getElementById("modal");
    $.post('/createplotpoint',
    {
        title: $('#plot_point_title').val(),
        summary: $('#plot_point_summary').val(),
        game_id: $('#game').val()
    },
    function(response) {
        let r = JSON.parse(response);
        console.log(r);
        modal.style.display = "none";
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    })
}

function create_reminder() {
    var modal = document.getElementById("modal");
    modal.style.display = "block";
    var div = $('#modal_content');
    $('#modal-header').html('Create Reminder')
    let html = "<form id='create_npc_form' method='post'>";
    html += "<table>";
    html += '<tr><td><label>Title:</label></td><td><input type="text" id="reminder_title" name="reminder_title"></td></td>';
    html += '<tr><td><label>Details:</label></td><td><textarea id="reminder_details" name="reminder_summary"></textarea></td></td>';
    html += '<tr><td><label>Trigger:</label></td><td><input type="text" id="reminder_trigger" name="reminder_trigger"></td></td>';
    html += '</table>';
    html += '<div><input type="button" value="Create" onclick="create_reminder_submit()"></div>';
    html += "</form>"
    div.html(html)
}

function create_reminder_submit() {
    // Get all the values from the form
    var modal = document.getElementById("modal");
    $.post('/createreminder',
    {
        title: $('#reminder_title').val(),
        details: $('#reminder_details').val(),
        trigger: $('#reminder_trigger').val(),
        game_id: $('#game').val()
    },
    function(response) {
        refresh_reminders();
        modal.style.display = "none";
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    })
}

function refresh_reminders() {
    $.post('/getreminders', {
        game_id: $('#game').val()
    }, function(response) {
        let r = JSON.parse(response);
        $('#reminder_list').html('')
        for (let i = 0; i < r.length; i++) {
            let reminder = r[i];
            let div = $('<div class="reminder">');
            let title = $('<div class="reminder_title">');
            let delete_ = $('<div class="reminder_delete" onclick="delete_reminder('+reminder.id+')">');
            delete_.html('X');
            title.html(reminder.title);
            div.append(delete_);
            div.append(title);
            $('#reminder_list').append(div);
        };
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    });
}

function delete_reminder(id) {
    $.post('/deletereminder', {
        id: id
    }, function(response) {
        refresh_reminders();
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    });
}

function refresh_notes_list() {
    $.post('/getnotes', {
        game_id: $('#game').val()
    }, function(response) {
        let r = JSON.parse(response);
        $('#notes').html(
            `<table id="table_notes">
                <tr>
                    <th>Date</th><th>Notes</th><th>Delete</th>
                </tr>`
        );
        r.forEach((row)=> {
            let date = row.date;
            let id = row.id;
            $('#table_notes').append(
                `<tr id="note_${date}">
                <td><a href="javascript:show_note('${date}', '${id}')">${date}</a></td>
                <td></td>
                <td>
                    <a href="javascript:delete_note('${date}')">X</a>
                </td>
                </tr>`
            );
        })
        $('#notes').append('</table>');
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    });
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
        let rnd = Math.random();
        let npc_img_html = (r['image_exists'])
            ? `<img src="/static/img/npc/${id}.png?${rnd}" class="npc_image"/><br/><a href="javascript:gen_npc_image('${id}')">Regenerate Image</a>`
            : '<a href="javascript:gen_npc_image(\''+id+'\')">Generate Image</a>';
        console.log(npc_img_html)
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
            val = r[k];
            console.log(val)
            if (val == null || val == 'null')
                val = '';
            html += '<tr class="npc"><td nowrap>' + key + `</td><td id="${id}_${k}">` + val + `</td><td><img src="/static/img/arrow-rotate-right-solid.svg"/ class="regen" onclick="regen_key(${id}, '${k}', this)"></td></tr>`;
        })
        if (r['summary'] == null)
            r['summary'] = 'No summary available. Generate one by clicking the refresh icon above.';
        html += '</table>';     
        html += `<div class="npc_summary">
            <div class="regen" title="Regenerate Summary" onclick="regen_summary('${id}')"></div>
            <div id="npc_summary">${r['summary']}</div>
            </div>`;
        html += `<div id="npc_image" class="npc_image">${npc_img_html}</div>`;
        html += '<div style="clear:both"></div>';
        div.html(html)
        div.removeClass('lds-ring')
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    })
}

function delete_name(id) {
    $.post('/deletename', { 
        id: id
    }, function(response) {
        if ($('#name_'+id))
            $('#name_'+id).remove();
        if ($('#game_name_'+id))
        $('#game_name_'+id).remove();
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    });
}

function add_name(id, background, name) {
    $.post('/addname', { 
        id: id,
        game_id: $('#game').val()
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
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    });;
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
    $('#modal-buttons').html('')
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
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
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
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    });
}

function gen_npc_image(id) {
    let div_img = $('#npc_image');
    div_img.html("Your image in being generated. This may take a few seconds...");

    $.post('/gennpcimage_stability', { 
        id: id
    }, function(response) {
        let div = $('.npc_image');
        let rnd = Math.random();
        div.html(`<img src="/static/img/npc/${id}.png?${rnd}" class="npc_image"/>`);
        link_regen = $('<a href="javascript:gen_npc_image(\''+id+'\')">');
        link_regen.html('Regenerate Image');
        div.append(link_regen);
    }).fail(function(jqXHR, textStatus, errorThrown) {
        div_img.html('An error occurred, please try again - ' + errorThrown);
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

function show_account() {
    var modal = document.getElementById("modal");
    modal.style.display = "block";
    var div = $('#modal_content');
    $('#modal-header').html('Account')
    let html = "<main class='account'>"
    html += "<nav>"
    html += "<ul>"
    html += "<li><a href='javascript:show_account_password()'>Change Password</a></li>"
    html += "<li><a href='javascript:show_account_membership()'>Membership</a></li>"
    html += "</ul>"
    html += "</nav>"
    html += "<article id='account_article'>"
    html += "<div id='account_content'>"
    html += "</div>"
    html += "</article>"
    html += "<div style='clear:both'></div>"
    html += "</main>"
    div.html(html)
    show_account_password();
}

function show_account_password() {
    let article = $('#account_article');
    let html = "<h1>Change Password</h1>"
    html += "<form id='account_form' method='post'>";
    html += "<table>";
    html += '<tr><td><label>Change Password:</label></td><td><input type="password" id="psw1" name="psw1"></td></td>';
    html += '<tr><td><label>Confirm Password:</label></td><td><input type="password" id="psw2" name="psw2"></td></td>';
    html += '</table>';
    html += '<div><input type="button" value="Save New Password" onclick="save_password()"></div>';
    html += "</form>"
    article.html(html)
}

function show_account_membership() {
    let article = $('#account_article');
    let html = "<h1>Membership</h1>"
    html += "<div id='subscriptions'>"

    var subscriptions = [
        {
            header: 'Free',
            price: 'Free',
            priceId: '',
            features: [
                '50 Chat Messages per Month',
                '5 NPCs',
                '1 Campaign',
                'Unlimited Session Notes',
                'Unlimited Reminders'
            ]
        },
        {
            header: 'Basic',
            price: '$10/month',
            priceId: 'price_1NXa5RIv1yyTRw7njvjcH7mc',
            features: [
                '500 Chat Messages per Month',
                '50 NPCs',
                '3 Campaigns',
                'Unlimited Session Notes',
                'Unlimited Reminders',
                'AI Note Taking from MP3 (1/Week)'
            ]
        }
    ];

    for (var i = 0; i < subscriptions.length; i++) {
        var subscription = subscriptions[i];
        let item_class = (subscription.header.toLowerCase() == membership_level.toLowerCase()) ? 'subscription-item selected' : 'subscription-item';
        html += "<div class='"+item_class+"' id='subscription-" + subscription.header.toLowerCase() + "'>";
        html += "<div class='subscription-header'>" + subscription.header + "</div>";
        html += "<div class='subscription-body'>";
        html += "<div class='subscription-price'>" + subscription.price + "</div>";
        html += "<div class='subscription-description'>";
        html += "<ul>";
        for (var j = 0; j < subscription.features.length; j++) {
            html += "<li>" + subscription.features[j] + "</li>";
        }
        html += "</ul>";
        html += "</div>"; // subscription-description
        html += "<div style='text-align:center'>"
        html += `<button style="background-color:#6772E5;color:#FFF;padding:8px 12px;border:0;border-radius:4px;font-size:1em;cursor:pointer"`
            + ` id="checkout-button-${subscription.priceId}"`
            + ` role="link"`
            + ` type="button">`
            + `Update Membership`
            + `</button>`;
        html += "</div>"; // subscription-button    
        html += "</div>"; // subscription-body
        html += "</div>"; // subscription-item
    }

    html += "<div style='clear:both'></div>"
    //html += "<div style='text-align:center'><input type='button' value='Update Membership' onclick='update_membership()' style='background: rgba(25, 25, 112, 1); border: none; color: white; padding: 15px 32px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; border-radius: 10px;'></div>"
    html += "</div>" // subscrptions
    html += "<div id='error-message'></div>";
    article.html(html)

    for (var i = 0; i < subscriptions.length; i++) {
        var subscription = subscriptions[i];
        $('#subscription-'+subscription.header.toLowerCase()).on('click', function() {
            $('.subscription-item').removeClass('selected');
            $(this).addClass('selected');
        });
        if (subscription.priceId != null)
            initialize_stripe_button(subscription.priceId);
    }
}

function save_password() {
    let psw1 = $('#psw1').val();
    let psw2 = $('#psw2').val();
    if (psw1 != psw2) {
        alert('Passwords do not match');
        return;
    }
    $.post('/savepassword', {
        password: psw1
    }, function(response) {
        alert('Password saved');
        close_modal();
    }).fail(function(jqXHR, textStatus, errorThrown) {
        alert('An error occurred, please try again - ' + errorThrown);
    });
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

function initialize_stripe_button(stripdId) {
    var stripe = Stripe(stripe_publishable_key);
    alert(stripe_publishable_key + "\n" + stripdId)
  
    var checkoutButton = document.getElementById('checkout-button-'+stripdId);
    checkoutButton.addEventListener('click', function () {
	    alert(stripdId);
      stripe.redirectToCheckout({
        lineItems: [{price: stripdId, quantity: 1}],
        mode: 'subscription',
        successUrl: window.location.protocol + '//dmscreen.net/success',
        cancelUrl: window.location.protocol + '//dmscreen.net/canceled',
      })
      .then(function (result) {
        if (result.error) {
          var displayError = document.getElementById('error-message');
          displayError.textContent = result.error.message;
        }
      });
    });
  }
