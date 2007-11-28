$(function(){

	// Check user function
  function userFn() {

		this.user = '';
		this.status = false;

		this.check = function() {
			var val = $("#id_username").val();
			if (val.length == 0) return;
			var msgbox = $("#usermsg");

      if (this.user != val) {
        msgbox.html('<img src="/site_media/images/loading.gif" />');
        msgbox.show();
        setTimeout(function() { checkuser(val) }, 500);
				this.user = val;
      }
		}

		function checkuser(val) {
   		$.get("/accounts/check_user/" + val + "/", function(data) {
     		data = $.parseJSON(data);
				if (!data['success']) {
					$("#usermsg").css("color", "red");
					$("#usermsg").text(data["error_message"]);
				} else {
					$("#usermsg").css("color", "green");
					$("#usermsg").html("Ok.");
					this.status = true;
				}
			});
		}
  }

	// Check passwords function
  function passwordFn() {
		this.status = false;

		this.check = function() {
			var msgbox = $("#passmsg2");
			var pass1 = $("#id_password1").val();
			var pass2 = $("#id_password2").val();

			if (pass1.length > 0 && pass2.length > 0) {
				if (pass1 != pass2) {
					msgbox.css("color", "red");
					msgbox.text("The passwords are not equal.");
				} else {
					msgbox.css("color", "green");
					msgbox.text("Ok.");	
					this.status = true;
				}
			} else if (pass1.length > 0 || pass2.length > 0) {
				msgbox.text("");
			}
			$("#passmsg1").text("");
		}
  }

  // On focus, light the focused input
  $(".required").focus(function() {
		$(this).css("background", "white");
  });  

  // On blur, unlight the focused input
  $(".required").blur(function() {
		$(this).css("background", "#E6E6E6");
  });  

	var user = new userFn();
	var pass = new passwordFn();
	$("#id_username").blur(user.check);
	$("#id_password1").blur(pass.check);
	$("#id_password2").blur(pass.check);

  $("#id_username").focus();

});
