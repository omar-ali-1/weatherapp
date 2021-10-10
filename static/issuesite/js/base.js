
var appUser;

function prepopulateFields(userIdToken, userID) {
  //console.log(userIdToken);
  $.ajax('/endpoints/prepopulateFields/', {
    /* Set header for the XMLHttpRequest to get data from the web server
    associated with userIdToken */
    headers: {
      'Authorization': 'Bearer ' + userIdToken
    }
  }).then(function(data){
    data = JSON.parse(data);
    if (data['zipcode']) {
      $('#input-zip').val(data['zipcode']);
    }
    if (data['phone']) {
      $('#input-phone').val(data['phone']);
    }
    if (data['receive_email'] && data['receive_email'] == 'on') {
      $('#check-receive-email').prop('checked', true);
    }
    if (data['receive_sms'] && data['receive_sms'] == 'on') {
      $('#check-receive-sms').prop('checked', true);
    }
    if (data['receive_reports'] && data['receive_reports'] == 'on') {
      $('#check-receive-reports').prop('checked', true);
    }
    if (data['receive_rain'] && data['receive_rain'] == 'on') {
      $('#check-receive-rain').prop('checked', true);
    }
    $('#name').empty();
    // console.log(data);
    // Iterate over user data to display user's notes from database.
    //console.log(data);
  });
}

$(function(){
  var backendHostUrl = 'http://localhost:8080';

  // Initialize Firebase
  var config = {
    apiKey: "AIzaSyDET7FwTOxLLJk0mp0lyl3UI-GjHyCgF1w",
    authDomain: "grow-weather-1536097729211.firebaseapp.com",
    databaseURL: "https://grow-weather-1536097729211.firebaseio.com",
    projectId: "grow-weather-1536097729211",
    storageBucket: "grow-weather-1536097729211.appspot.com",
    messagingSenderId: "994489927427"
  };


  // This is passed into the backend to authenticate the user.
  var userIdToken = null;

  // Firebase log-in
  function configureFirebaseLogin() {

    firebase.initializeApp(config);
    //console.log("configurefirebaselogin");
    // console.log(firebase);

    // [START onAuthStateChanged]
    firebase.auth().onAuthStateChanged(function(user) {
      if (user) {
        $('#navbar-signIn').hide();
        $('#signed-in-dropdown').show();
        var profileLink = "/users/" + user.uid + "/";
        $("#my-profile").attr("href", profileLink );
        $('#signInModal').modal('hide')
        $('#navbar-profile').show();
        $('#navbar-sign-out-2').show();
        $('#settings-form').show();
        $('#navbar-sign-out-2').show();
        $('#sign-in-welcome').hide();
        
        var name = user.displayName;
        user.getIdToken().then(function(idToken) {
          // console.log(idToken);
          prepopulateFields(idToken, user.uid);
          //prepopulateFields(idToken, user.uid);
        });
        /* If the provider gives a display name, use the name for the
        personal welcome message. Otherwise, use the user's email. */
        var welcomeName = name ? name : user.email;



      } else {
        currentUser = null;
        $('#navbar-signIn').show();
        $('#signed-in-dropdown').hide();
        $("#my-profile").attr("href", "/" );
        $('#navbar-profile').hide();
        $('#navbar-sign-out-2').hide();
        $('#settings-form').hide();
        $('#sign-in-welcome').show();



        //$('#logged-in').hide();
        //$('#logged-out').show();

      }
    // [END onAuthStateChanged]

    });

    firebase.auth().onAuthStateChanged(function(user) {
      if (user) {
        var name = user.displayName;
        var welcomeName = name ? name : user.email;
        currentUser = user;
        $('#user-name').html(welcomeName);
        $('#user-image').attr("src", user.photoURL);
        $('#user-name').show();
        $('#user-image').show();

        currentUser.getIdToken().then(function(idToken) {

        });
        /* If the provider gives a display name, use the name for the
        personal welcome message. Otherwise, use the user's email. */
        var welcomeName = name ? name : user.email;



      } else {
        $('#user-name').hide();
        $('#user-image').hide();
        currentUser = null;
      }
    // [END onAuthStateChanged]

    });



  }

  // [START configureFirebaseLoginWidget]
  // Firebase log-in widget
  function configureFirebaseLoginWidget() {
    // console.log("widgeeeet");
    var uiConfig = {
      callbacks: {
        signInSuccess: function(currentUser, credential, redirectUrl) {
          // console.log("signed in...");
          // console.log(redirectUrl);
          // User successfully signed in.
          // Return type determines whether we continue the redirect automatically
          // or whether we leave that to developer to handle.
          $('.navbar-toggler').click();
          currentUser.getIdToken().then(function(idToken) {
                    //console.log(userIdToken);
                    //console.log("Token:");
                    //console.log(idToken);
                    //$('#user').text(welcomeName);
                    //$('#logged-in').show();
                    verifyOrCreateUser(idToken, currentUser.uid);


                  });



          function verifyOrCreateUser(userIdToken, userID) {
            //console.log(userIdToken);
            $.ajax('/endpoints/verifyOrCreateUser/', {
              /* Set header for the XMLHttpRequest to get data from the web server
              associated with userIdToken */
              headers: {
                'Authorization': 'Bearer ' + userIdToken
              }
            }).then(function(data){
              //
            });
          }
          return false;
        },
        uiShown: function() {
          // The widget is rendered.
          // Hide the loader.
        }
      },
      // Will use popup for IDP Providers sign-in flow instead of the default, redirect.
      signInFlow: 'popup',
      //signInSuccessUrl: '/',
      signInOptions: [
        // Leave the lines as is for the providers you want to offer your users.
        {
          provider: firebase.auth.GoogleAuthProvider.PROVIDER_ID,
          scopes: [
            'https://www.googleapis.com/auth/plus.login'
          ],
          customParameters: {
            // Forces account selection even when one account
            // is available.
            prompt: 'select_account'
          }
        }
        // firebase.auth.PhoneAuthProvider.PROVIDER_ID
      ],
      // Terms of service url.
      tosUrl: '<your-tos-url>'
    };
    try {
        ui = new firebaseui.auth.AuthUI(firebase.auth());
    }
    catch(err) {
        //
    }
    
    ui.start('#firebaseui-auth-container', uiConfig);
  }
  // [END configureFirebaseLoginWidget]


  configureFirebaseLogin();
  configureFirebaseLoginWidget();


    firebase.auth().onAuthStateChanged(function(user) {
      appUser = user;
    });

  var signOutBtn2 = $('#sign-out-2');
  signOutBtn2.click(function(event) {
    event.preventDefault();
    $('.navbar-toggler').click();
    firebase.auth().signOut().then(function() {
      //console.log("Sign out successfullllll");
      $('#input-zip').val('');
  
  
      $('#input-phone').val('');
  
  
      $('#check-receive-email').prop('checked', false);
  
  
      $('#check-receive-sms').prop('checked', false);
  
  
      $('#check-receive-reports').prop('checked', false);
  
  
      $('#check-receive-rain').prop('checked', false);
  
      $('#user-name').empty();
      $('#update-message').empty();
      configureFirebaseLoginWidget();

    }, function(error) {
      console.log(error);
    });
  });
});



function updateUser(data) {
  //console.log("updateUser");
  //console.log($( "#settings-form" ).attr("action"));
  try {
    appUser.getIdToken().then(function(idToken) {
      $.ajax({
          url: $( "#settings-form" ).attr("action"),
          type: 'post',
          data: data,
          headers: {
              'Authorization': 'Bearer ' + idToken
          },
          dataType: 'json',
        beforeSend: function() {
          $('#save-settings').attr('disabled', 'disabled');
          $('#resend-report').attr('disabled', 'disabled');
          $('#update-message').html('');
          $('#spinner-container').show();
          addSpinner($('#spinner-container'));
        },
        complete: function(){
          $('#save-settings').removeAttr('disabled', 'disabled');
          $('#resend-report').removeAttr('disabled', 'disabled');
          removeSpinner($('#spinner-container'));
          $('#spinner-container').hide();

        },
        success: function (data) {
            //console.info(data);
            if (data['err']) {
              message = data['err'];
              //console.info("in here");
            } else {
              message = 'Success!';
            };
        //console.info("over here");
        $('#update-message').html(message);
        $('#update-message').show();
        },
        error: function(request, status, errorThrown) {
          //console.info("eroooor");
          $('#issue-message').html(errorThrown);
          $('#issue-message').show();
        }
      });
          });
  }
  catch(err) {
    $('#update-message').html(err);
    $('#issue-message').show();
  };


};

function resendReport(data) {
  //console.log("updateUserSettings");
  //console.log($( "#settings-form" ).attr("action"));
  try {
    resendURL = '/endpoints/resendReport/';
    appUser.getIdToken().then(function(idToken) {
      $.ajax({
          url: resendURL,
          type: 'get',
          headers: {
              'Authorization': 'Bearer ' + idToken
              //'Cookie': 'csrftoken={{ csrf_token }}'
          },
          dataType: 'json',
        beforeSend: function() {
          $('#resend-report').attr('disabled', 'disabled');
          $('#save-settings').attr('disabled', 'disabled');
          $('#update-message').html('');
          $('#spinner-container').show();
          addSpinner($('#spinner-container'));
        },
        complete: function(){
          $('#resend-report').removeAttr('disabled', 'disabled');
          $('#save-settings').removeAttr('disabled', 'disabled');
          removeSpinner($('#spinner-container'));
          $('#spinner-container').hide();

        },
        success: function (data) {
            //console.info(data);
            if (data['err']) {
              message = data['err'];
              //console.info("in here");
            } else {
              message = 'Success!';
            };
        //console.info("over here");
        $('#update-message').html(message);
        $('#update-message').show();
        },
        error: function(request, status, errorThrown) {
          //console.info("eroooor");
          $('#issue-message').html(errorThrown);
          $('#issue-message').show();
        }
      });
          });
  }
  catch(err) {
    $('#update-message').html(err);
    $('#issue-message').show();
  };


};



// Event Handlers

$( "#settings-form" ).on( "submit", function( event ) {
  event.preventDefault();
  //console.log(this);
  var data = $( this ).serialize();
  //console.log(data);
  updateUser(data);
});


$( "#resend-report" ).on( "click", function( event ) {
  event.preventDefault();
  //console.log(this);
  //var data = $( this ).serialize();
  //console.log(data);
  resendReport();
  //getHistory();
});




/*
function getHistory(data) {
  //console.log("updateUserSettings");
  //console.log($( "#settings-form" ).attr("action"));
  try {
    resendURL = '/endpoints/getAlertHistory/';
    appUser.getIdToken().then(function(idToken) {
      $.ajax({
          url: resendURL,
          type: 'get',
          headers: {
              'Authorization': 'Bearer ' + idToken
              //'Cookie': 'csrftoken={{ csrf_token }}'
          },
          dataType: 'json',
        beforeSend: function() {
          $('#resend-report').attr('disabled', 'disabled');
          $('#save-settings').attr('disabled', 'disabled');
          $('#update-message').html('');
          $('#spinner-container').show();
          addSpinner($('#spinner-container'));
        },
        complete: function(){
          $('#resend-report').removeAttr('disabled', 'disabled');
          $('#save-settings').removeAttr('disabled', 'disabled');
          removeSpinner($('#spinner-container'));
          $('#spinner-container').hide();

        },
        success: function (data) {
            //console.info(data);
            if (data['err']) {
              message = data['err'];
              //console.info("in here");
            } else {
              message = data['alerts'];
            };
        //console.info("over here");
        $('#update-message').html(message);
        $('#update-message').show();
        },
        error: function(request, status, errorThrown) {
          //console.info("eroooor");
          $('#issue-message').html(errorThrown);
          $('#issue-message').show();
        }
      });
          });
  }
  catch(err) {
    $('#update-message').html(err);
    $('#issue-message').show();
  };


};
*/