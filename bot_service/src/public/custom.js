(function() {
    var startingTime = new Date().getTime();
    // Load the script
    var script = document.createElement("SCRIPT");
    script.src = 'https://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js';
    script.type = 'text/javascript';
    script.onload = function() {
    	var $ = window.jQuery;
      $(function() {
	//            var endingTime = new Date().getTime();
  //          var tookTime = endingTime - startingTime;
    //        window.alert("jQuery is loaded, after " + tookTime + " milliseconds!");

			console.log("jQuery Loaded");

			jQuery(window).load(function(){
				console.log("Window Loaded");
				console.log(jQuery(".MuiInputAdornment-root").length);
				jQuery(".MuiInputAdornment-root").prepend("<span><button id='browse_prompt' name='browse_prompt' onClick='browsePrompt()'>Browse Prompts</button></span>");
			});

			function browsePrompt(){
				
				console.log("ready to fly");

			}

        });
    };
    document.getElementsByTagName("head")[0].appendChild(script);
})();