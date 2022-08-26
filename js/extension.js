(function() {
	class Hotspot extends window.Extension {
	    constructor() {
	      	super('hotspot');
			//console.log("Adding hotspot addon to menu");
      		
            this.debug = false;
            
			this.addMenuEntry('Candle Hotspot');
			
            this.interval = null;
            
			this.attempts = 0;

	      	this.content = '';
            this.animals = undefined;
            this.master_blocklist = [];
			this.current_time = 0;
            
            this.seconds = 0;
            this.aborted = false;
            this.launched = false;
            this.cable_needed = false;

			fetch(`/extensions/${this.id}/views/content.html`)
	        .then((res) => res.text())
	        .then((text) => {
	         	this.content = text;
	  		 	if( document.location.href.endsWith("hotspot") ){
					//console.log(document.location.href);
                    setTimeout(() => {
                        this.show();
                    }, 3000);
	  		  		
                    
	  		  	}
	        })
	        .catch((e) => console.error('Failed to fetch content:', e));
	    }

		
		/*
		hide(){
			clearInterval(this.interval);
			this.view.innerHTML = "";
		}
		*/
		hide() {
			//console.log("hotspot hide called");
			try{
                this.attempts = 0;
				clearInterval(this.interval);
				//console.log("interval cleared");
                
			}
			catch(e){
				//console.log("no interval to clear? " + e);
			}
            this.interval = null;
		}
		

	    show() {
			//console.log("hotspot show called");
			//console.log("this.content:");
			//console.log(this.content);
            
            
            const main_view = document.getElementById('extension-hotspot-view');

            
			try{
				clearInterval(this.interval);
			}
			catch(e){
				//console.log("no interval to clear?: " + e);
			}
			
			
			
			if(this.content == ''){
                //console.log("- show: empty content, aborting");
				return;
			}
			else{
				//document.getElementById('extension-hotspot-view')#extension-hotspot-view
				main_view.innerHTML = this.content;
			}
			
			
			const list = document.getElementById('extension-hotspot-list');
			const pre = document.getElementById('extension-hotspot-response-data');
            const blocklist = document.getElementById('extension-hotspot-blocklist');

            //console.log("blocklist:");
            //console.log(blocklist);
            
            
            document.getElementById('extension-hotspot-retry-init-button').addEventListener('click', (event) => {
                this.get_init_data();
            });
            
            
            
            document.getElementById('extension-hotspot-title').addEventListener('click', (event) => {
                this.get_init_data();
            });


			document.getElementById('extension-hotspot-refresh-button').addEventListener('click', (event) => {
				//console.log("refresh button clicked");
				this.get_latest();
			});

            
            
            // Abort button
			document.getElementById('extension-hotspot-abort-button').addEventListener('click', (event) => {
				//console.log("abort button clicked");
		        window.API.postJson(
		          `/extensions/hotspot/api/ajax`,
					{'action':'abort'}

		        ).then((body) => {
					if(this.debug){
                        console.log("abort response: ", body);
                    }
                    this.aborted = true;
                    document.getElementById('extension-hotspot-abort-message').innerText = "Launch was aborted ";
                    
		        }).catch((e) => {
		  			//console.log("Error sending abort command: " + e.toString());
					document.getElementById('extension-hotspot-abort-message').innerText = "Error sending abort command: " + e.toString();
		        });
                
			});
				
            
            
            // Launch button
			document.getElementById('extension-hotspot-launch-button').addEventListener('click', (event) => {
				//console.log("launch button clicked");
                
		        window.API.postJson(
		          `/extensions/hotspot/api/ajax`,
					{'action':'launch'}

		        ).then((body) => {
                    if(this.debug){
                        console.log("launch now response:", body);
                    }
					
                    this.aborted = true;
                    document.getElementById('extension-hotspot-abort-message').innerText = "Launching...";
                    this.seconds = 89;
                    
		        }).catch((e) => {
		  			//console.log("Error sending abort command: " + e.toString());
					document.getElementById('extension-hotspot-abort-message').innerText = "Error sending abort command: " + e.toString();
		        });
                
			});
                
                
                
            // Listen for changes in dropdowns
            main_view.addEventListener('change', function(event) {
                //console.log(event);
                if (event.target.tagName.toLowerCase() === 'select') {
                    //console.log("clicked on select. value: " + event.target.value);
                    const target = event.target;
      				
                    window.API.postJson(
      					`/extensions/hotspot/api/ajax`,
      					{'action':'set_permission','domain':target.dataset.domain, 'permission':target.value, 'mac':target.dataset.mac}
      				).then((body) => { 
      					//console.log("update permission reaction: ");
      					//console.log(body); 
      					if( body['state'] != true ){
      						pre.innerText = body['message'];
      					}

      				}).catch((e) => {
      					//console.log("hotspot: error in dropdown permissions handler");
      					pre.innerText = e.toString();
      				});
  
                  
                }
                else if (event.target.tagName.toLowerCase() === 'option') {
                    //console.log("clicked on option");
                }
            });
                
                
                
            // Listen for remove buttons clicks in blocklist
            blocklist.addEventListener('click', function(event) {
                //console.log(event);
                if (event.target.tagName.toLowerCase() === 'button') {
                      
                    if( event.target.innerText == 'unblock'){
                        //console.log("clicked on unblock button.");
                      
                        const target = event.target;
                  
                        //console.log("removing: " + target.dataset.domain);
                      
          				window.API.postJson(
          					`/extensions/hotspot/api/ajax`,
          					{'action':'remove_from_master_blocklist','domain':target.dataset.domain}
          				).then((body) => { 
                            if(this.debug){
          					    console.log("remove from blocklist response: ", body);
                            }
          					//console.log(body); 
          					if( body['state'] != true ){
          						pre.innerText = body['message'];
                              }
                              else{
                                  //console.log("should remove from list: " + target.dataset.domain);
                                  //this.get_latest();
                                
                                  const blocklist_children = document.getElementById("extension-hotspot-blocklist").children;
                                  for (var i = 0; i < blocklist_children.length; i++) {
                                      var child = blocklist_children[i];
                                      if( child.dataset.domain == target.dataset.domain ){
                                          document.getElementById("extension-hotspot-blocklist").removeChild(child);
                                      }    
                                  }
                              }

          				}).catch((e) => {
          					//console.log("hotspot: error in remove from blocklist handler");
          					pre.innerText = e.toString();
          				});
                    }
                }
            });
            
            
		
		    
			
			
            
            


			// TABS

			document.getElementById('extension-hotspot-tab-button-timers').addEventListener('click', (event) => {
				//console.log(event);
				document.getElementById('extension-hotspot-content').classList = ['extension-hotspot-show-tab-timers'];
			});
			document.getElementById('extension-hotspot-tab-button-satellites').addEventListener('click', (event) => {
				document.getElementById('extension-hotspot-content').classList = ['extension-hotspot-show-tab-satellites'];
			});
			document.getElementById('extension-hotspot-tab-button-tutorial').addEventListener('click', (event) => {
				document.getElementById('extension-hotspot-content').classList = ['extension-hotspot-show-tab-tutorial'];
			});

            
            //console.log("evil");
            this.get_init_data();
           

		} //  end of show()
		
	


        get_init_data(){
            //console.log("in get_init_data");
            
	        window.API.postJson(
	          `/extensions/hotspot/api/ajax`,
				{'action':'init'}

	        ).then((body) => {
				//console.log("hotspot init response: ", body);
                
                if(typeof body.debug !='undefined'){
                    this.debug = body.debug;
    			    if(body.debug){
                        console.log("hotspot init response: ", body);
    			        document.getElementById('extension-hotspot-debug-warning').classList.remove('extension-hotspot-hidden');
                        document.getElementById('extension-hotspot-response').classList.remove('extension-hotspot-hidden');
    			    }
                }
                
                // Cable needed?
                if(typeof body.cable_needed !='undefined'){
				    if(body.cable_needed){
                        this.cable_needed = body.cable_needed;
				        document.getElementById('extension-hotspot-cable-tip').classList.remove('extension-hotspot-hidden');
				    }
                    else{
        				if(typeof body.ssid !='undefined'){
        				    if(body.ssid){
        				        document.getElementById('extension-hotspot-ssid').innerText = body.ssid;
                                document.getElementById('extension-hotspot-password').innerText = body.password;
                                document.getElementById('extension-hotspot-ssid-container').classList.remove('extension-hotspot-hidden');
                                if(body.password == 'iloveprivacy'){
                                    document.getElementById('extension-hotspot-change-password-hint').classList.remove('extension-hotspot-hidden');
                                }
        				    }
        				}
                        
                        
                        
                        // Get latest list
                        this.get_latest();
                
                        // Create the interval for the countdown timer
                        if(this.interval == null){
                			this.interval = setInterval(function(){
                				//this.get_latest();
                
                                this.seconds++;
                                //console.log(this.seconds);
                
                                if(this.seconds < 90 && this.aborted == false && this.cable_needed == false){
                                    document.getElementById('extension-hotspot-countdown-seconds').innerText = 90 - this.seconds;
                                    document.getElementById('extension-hotspot-countdown').classList.remove('extension-hotspot-hidden');
                                }
                                else{
                                    document.getElementById('extension-hotspot-countdown').classList.add('extension-hotspot-hidden');
                                    if(this.launched == false){
                                        this.launched = true;
                                        this.regenerate_items();
                                    }
                                }
                			}.bind(this), 1000);
                        }
                        
                        
                    }
                    
				}
                
                document.getElementById('extension-hotspot-connection-error').classList.add('extension-hotspot-hidden');
    			
                
                
	        }).catch((e) => {
	  			//console.log("Error sending abort command: " + e.toString());
				document.getElementById('extension-hotspot-abort-message').innerText = "Hotspot: Error getting init data: " + e.toString();
                console.log("Hotspot: Error getting init data: " + e.toString());
                if(document.getElementById('extension-hotspot-connection-error') != null){
                    document.getElementById('extension-hotspot-connection-error').classList.remove('extension-hotspot-hidden');
                }
                else{
                    console.log("Hotspot: error, could not even show the connection error");
                }
                
                setTimeout(() => {
                    console.log("attempting to get init data again after previous attemp failed 10 seconds ago");
                    this.get_init_data();
                }, 10000);
                
                
                // Get latest list
                //this.get_latest();
	        });
            
            
        }


        
        
        get_latest(){
            //console.log("hotspot: in get_latest");
            const main_view = document.getElementById('extension-hotspot-view');
            const pre = document.getElementById('extension-hotspot-response-data');
			
            try{
		  		// Get list of items
				if(this.attempts < 3){
					this.attempts++;
					//console.log(this.attempts);
					//console.log("calling")
			        window.API.postJson(
			            `/extensions/${this.id}/api/ajax`,
					    {'action':'latest'}

			        ).then((body) => {
						if(this.debug){
                            console.log("Hotspot Python API /latest result:");
    						console.log(body);
						}
                        
						this.attempts = 0;
                        
						if(body['state'] == true){
							this.animals = body['animals'];
                            this.protected_animals_count = body['protected_animals_count'];
                            this.master_blocklist = body['master_blocklist'];
                            pre.innerText = body['message'];
                            this.seconds = body['seconds'];								
							
                            this.regenerate_items();
			
						}
						else{
							//console.log("not ok response while getting items list");
							pre.innerText = body['update'];
						}

			        }).catch((e) => {
			  			console.log("Error getting latest: " + e.toString());
						//console.log(e);
						pre.innerText = "Loading items failed - connection error";
						this.attempts = 0;
			        });	
				}
				else{
					pre.innerText = "Lost connection.";
				}
                
			}
            catch(e){ 
                console.log("Hotspot polling error: ", e);
            }
            
        }
        
	
	
	
		//
		//  REGENERATE ITEMS
		//
	    regenerate_items(){
            try {
                //console.log("inn regenerate_items");
    			const pre = document.getElementById('extension-hotspot-response-data');
    			const list = document.getElementById('extension-hotspot-list');
    			const original = document.getElementById('extension-hotspot-original-item');
                const original_domain_item = document.getElementById('extension-hotspot-original-domain-item');
                const blocklist = document.getElementById('extension-hotspot-blocklist');
            
            
            
            
            
            
            
            
            
                //
                //  UPDATE BLOCKLIST
                //
            
            
				//var domain_clone = original_domain_item.cloneNode(true);
				//domain_clone.removeAttribute('id');
                //console.log("domain_clone:");
                //console.log(domain_clone);
                
                
                // domain
                

                //domain_clone.querySelectorAll( '.extension-hotspot-domain-domain' )[0].appendChild(s);
                
                //console.log(this.animals[mac]['domains'][domain]);
                //console.log(this.animals[mac]['domains'][domain]['timestamps']);
                
                
                // count
                
                //const master_blocklist_length = this.master_blocklist.length;
                //console.log("master_blocklist_length = " + master_blocklist_length);
                
                //console.log("__timestamps__");
                //console.log(this.animals[mac]['domains'][domain]['timestamps']);
                //console.log("domain_count: " + domain_count);
                
                //var q = document.createElement("span");
                //var q = document.createTextNode(this.animals[mac]['domains'][domain]['timestamps'].length);
                //q.appendChild(w);
                //domain_clone.querySelectorAll( '.extension-hotspot-domain-count' )[0].appendChild(q);

				//clone.querySelectorAll( '.extension-hotspot-domains' )[0].appendChild(domain_clone);
                
                //const select_options = ['blocked','allowed'];
                //var select = document.createElement("select");
                //select.setAttribute("class", "extension-hotspot-domains-permission-select");
                //select.setAttribute("data-domain", domain);
                //select.setAttribute("data-mac", mac);

                blocklist.innerHTML = "";
                for (let i = 0; i < this.master_blocklist.length; i++) {
                    //console.log("[] adding " + select_options[i]);
                    //select.options.add(new Option(select_options[i], select_options[i]));
                    const domain = this.master_blocklist[i];
                    
                    var f = document.createElement("div");
                    f.setAttribute("data-domain", domain);
                    var y = document.createElement("span");
                    var s = document.createTextNode(domain);
                    y.appendChild(s);
                    f.appendChild(y);
                
                    var g = document.createElement("button");
                    g.setAttribute("data-domain", domain);
                    g.setAttribute("class", "extension-hotspot-button extension-hotspot-blocklist-remove-button");
                    var h = document.createTextNode("unblock");
                    g.appendChild(h);
                    f.appendChild(g);
                    
                    blocklist.appendChild(f); 
                            
                }
                
                /*
                var remove_buttons = document.getElementsByClassName("extension-hotspot-blocklist-remove-button");

                for (var i = 0; i < remove_buttons.length; i++) {
                    (function () {
                        remove_buttons[i].addEventListener("click", function() { makeItHappen(boxa,boxb); }, false);
                        elem[k].addEventListener("click", function() { makeItHappen(boxb,boxa); }, false);
                    }()); // immediate invocation
                }
                */
                
				
			  	//});
                
                //domain_clone.querySelectorAll( '.extension-hotspot-domain-permission' )[0].appendChild(select);
            
            
            
            
            
            
                //
                //  UPDATE DEVICES
                //
                
                list.innerHTML = "";
                //console.log(".")
                //console.log("..")
                //console.log("animals:");
                //console.log(this.animals);
                //console.log("looping over animals now:");
                
                const keys = Object.keys(this.animals);

                // print all keys
                //console.log(keys);

                //console.log("Active for more than 90 seconds. Currently no devices connected.");
                if(keys.length == 0 ){
					list.innerHTML = '<div class="extension-hotspot-centered-page" style="text-align:center"><p>There are currently no devices on the hotspot network.</p></div>';
				    return;
                }



                // iterate over object
                keys.forEach((mac, index) => {
                    //console.log(`${mac}: ${this.animals[mac]}`);

					var clone = original.cloneNode(true);
					clone.removeAttribute('id');

                    //var protected_animal = false;
                    //if( this.animals[mac].hasOwnProperty('protected') ){
                    //    protected_animal = true;
                    //}
                    
                    const animal_parts = Object.keys(this.animals[mac]);
                    //console.log("animal parts: ");
                    //console.log(animal_parts)
					animal_parts.forEach((info, index2) => {
                        if(info == 'nicename' || info == 'vendor' || info == 'mac'){
                            //console.log(`${info}: ${this.animals[mac][info]}`);
                            if(info == 'vendor' && this.animals[mac][info] == 'unknown'){
                                return;
                            }
                            
                            var s = document.createElement("span");
                            //s.classList.add('extension-hotspot-nice-name-span');      
                            var t = document.createTextNode(this.animals[mac][info]);
                            s.appendChild(t);
                            
                            const selector_name = '.extension-hotspot-' + info;
                            var target_element = clone.querySelectorAll( selector_name )[0];
                            target_element.appendChild(s);
                        }
                        else if( info == 'ip' ){
                            var a = document.createElement("a");
                            a.classList.add('extension-hotspot-ip-link');
                            const url = window.location.href;
                            a.href = url.split("/")[0] + '//' + this.animals[mac][info]
                            var h = document.createTextNode(this.animals[mac][info]);
                            a.appendChild(h);
                            
                            const selector_name = '.extension-hotspot-' + info;
                            var target_element = clone.querySelectorAll( selector_name )[0];
                            target_element.appendChild(a);
                        }
                        else if(info == 'protected'){
                            clone.querySelectorAll( '.extension-hotspot-domains' )[0].innerHTML = '<p class="extension-hotspot-privacy-warning">This device has connected to so many domains that it may be a laptop, tablet or mobile phone. To safeguard privacy its connection log will not be shown.</p>';
                            clone.querySelectorAll( '.extension-hotspot-item-clear-button' )[0].remove();
                            
                        }
                        else if(info == 'domains'){
                            try{
                                //console.log("generating domains list");
                                //console.log(this.animals[mac]['domains']);
                                const domains_list = Object.keys(this.animals[mac]['domains']);
                                //console.log("keys:");
                                //console.log(domains_list);
                                domains_list.forEach((domain, index3) => {
                                    
                					var domain_clone = original_domain_item.cloneNode(true);
                					domain_clone.removeAttribute('id');
                                    //console.log("domain_clone:");
                                    //console.log(domain_clone);
                                    
                                    
                                    // domain
                                    
                                    //var s = document.createElement("span");
                                    var s = document.createTextNode(domain);
                                    //s.appendChild(t);
                                    domain_clone.querySelectorAll( '.extension-hotspot-domain-domain' )[0].appendChild(s);
                                    
                                    //console.log(this.animals[mac]['domains'][domain]);
                                    //console.log(this.animals[mac]['domains'][domain]['timestamps']);
                                    
                                    
                                    // count
                                    
                                    const domain_count = this.animals[mac]['domains'][domain]['timestamps'].length;
                                    //console.log("__timestamps__");
                                    //console.log(this.animals[mac]['domains'][domain]['timestamps']);
                                    //console.log("domain_count: " + domain_count);
                                    
                                    //var q = document.createElement("span");
                                    var q = document.createTextNode(this.animals[mac]['domains'][domain]['timestamps'].length);
                                    //q.appendChild(w);
                                    domain_clone.querySelectorAll( '.extension-hotspot-domain-count' )[0].appendChild(q);

                					clone.querySelectorAll( '.extension-hotspot-domains' )[0].appendChild(domain_clone);
                                    
                                    const select_options = ['blocked','allowed'];
                                    var select = document.createElement("select");
                                    select.setAttribute("class", "extension-hotspot-domains-permission-select");
                                    select.setAttribute("data-domain", domain);
                                    select.setAttribute("data-mac", mac);

                                    for (let i = 0; i < select_options.length; i++) {
                                        //console.log("[] adding " + select_options[i]);
                                        //select.options.add(new Option(select_options[i], select_options[i]));
                                        var option = document.createElement("option");
                                                option.value = select_options[i];
                                                option.text = select_options[i];
                                                if (select_options[i] ==  'blocked' && this.master_blocklist.indexOf(domain) >= 0) {
                                                    option.selected = true;
                                                }
                                                else if( select_options[i] == this.animals[mac]['domains'][domain]['permission'] ){
                                                    //console.log("setting selected option");
                                                    option.selected = true;
                                                }
                                                select.appendChild(option);
                                                
                                                
                                    }
                                    
                                    domain_clone.querySelectorAll( '.extension-hotspot-domain-permission' )[0].appendChild(select);
                                    
                                    /*
                					const permission_select = clone.querySelectorAll('.extension-hotspot-domains-permission-select')[0];
                                    //console.log("adding change event listener to dropdown:");
                                    //console.log(permission_select);
                					permission_select.addEventListener('click', (event) => {
                                        //console.log("change detected");
                                        event.stopImmediatePropagation();
                                        
                                        //target.dataset.domain
                                        
                                        
                						var target = event.currentTarget;
                                        //console.log(target);
                                        
                                        
                						//var parent3 = target.parentElement.parentElement.parentElement;
                						//parent3.classList.add("delete");
                						//var parent4 = parent3.parentElement;
                						//parent4.removeChild(parent3);
					                    
                                        //console.log(target.dataset.domain);
                                        //console.log(target.dataset.mac);
                                        
                                        
                						// Send new values to backend
                						window.API.postJson(
                							`/extensions/${this.id}/api/ajax`,
                							{'action':'set_permission','domain':target.dataset.domain, 'permission':target.value, 'mac':target.dataset.mac}
                						).then((body) => { 
                							//console.log("update permission reaction: ");
                							//console.log(body); 
                							if( body['state'] != true ){
                								pre.innerText = body['message'];
                							}

                						}).catch((e) => {
                							//console.log("hotspot: error in save items handler");
                							pre.innerText = e.toString();
                						});
					
					
                				  	});
                                    */
                                    
                                    
                                });
                            }
                            catch(e){
                                //console.log("Error while creating domains list: ");
                                //console.log(e);
                            }

                        }

                    });
                        
                        
                    
                    
                    
                    
					// Add delete button click event
					const clear_button = clone.querySelectorAll('.extension-hotspot-item-clear-button')[0];
                    if(clear_button){
    					clear_button.addEventListener('click', (event) => {
                        
                            if (confirm('Delete/Reset the record of this device\'s activities? This will not affect which servers are blocked in the blocklist.')) {
                            
                                //console.log('Reset!');
                          
        						window.API.postJson(
        							`/extensions/hotspot/api/ajax`,
        							{'action':'clear','mac':mac}
        						).then((body) => { 
        							//console.log("clear item reaction: ");
        							//console.log(body);
        							if( body['state'] != true ){
        								pre.innerText = body['message'];
        							}
                                    else{
                                        this.get_latest();
                                    }

        						}).catch((e) => {
        							//console.log("hotspot: error in clear device handler");
        							pre.innerText = e.toString();
        						});
                        
                            }
                        
                            /*
    						var target = event.currentTarget;
    						var parent3 = target.parentElement.parentElement.parentElement;
    						parent3.classList.add("delete");
    						var parent4 = parent3.parentElement;
    						parent4.removeChild(parent3);
    					    */
                        
    						// Send new values to backend

    				  	});
                    }
					
                    
                    
                    
					// Add delete button click event
					const delete_button = clone.querySelectorAll('.extension-hotspot-item-delete-button')[0];
					delete_button.addEventListener('click', (event) => {
                        
                        if (confirm('Delete/Reset the record of this device\'s activities? This will not affect which servers are blocked in the blocklist.')) {
                            
                            //console.log('Reset!');
                          
    						window.API.postJson(
    							`/extensions/hotspot/api/ajax`,
    							{'action':'delete','mac':mac}
    						).then((body) => { 
    							//console.log("delete item reaction: ");
    							//console.log(body);
    							if( body['state'] != true ){
    								pre.innerText = body['message'];
    							}
                                else{
                                    this.get_latest();
                                }

    						}).catch((e) => {
    							//console.log("hotspot: error in delete device handler");
    							pre.innerText = e.toString();
    						});
                        
                        }
                        
                        /*
						var target = event.currentTarget;
						var parent3 = target.parentElement.parentElement.parentElement;
						parent3.classList.add("delete");
						var parent4 = parent3.parentElement;
						parent4.removeChild(parent3);
					    */
                        
						// Send new values to backend

					
					
				  	});
                    
                    
					/*
					clone.classList.add('extension-hotspot-type-' + type);
					//clone.querySelectorAll('.extension-hotspot-type' )[0].classList.add('extension-hotspot-icon-' + type);
					clone.querySelectorAll('.extension-hotspot-sentence' )[0].innerHTML = sentence;

					var time_output = "";
				
				
					if( clock.seconds_to_go >= 86400 ){
					
						const month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
					
						time_output += '<div class="extension-hotspot-date"><span class="extension-hotspot-day">' + clock.day + '</span>';
						time_output += '<span class="extension-hotspot-month">' + month_names[clock.month - 1] + '</span></div>';
						
					}

					
					var spacer = "";
					
					if(clock.hours < 10){spacer = "0";}
					time_output += '<div class="extension-hotspot-short-time"><span class="extension-hotspot-hours">' + spacer + clock.hours + '</span>';
				
					spacer = "";
					if(clock.minutes < 10){spacer = "0";}
					time_output += '<span class="extension-hotspot-minutes">' + spacer + clock.minutes + '</span></div>';


					// Show time to go
					if( clock.seconds_to_go < 86400 ){
						
						time_output += '<div class="extension-hotspot-time-to-go">'
						
						if( clock.seconds_to_go > 300 ){
							time_output += '<span class="extension-hotspot-hours-to-go">' + Math.floor(clock.seconds_to_go / 3600) + '</span>';
						}
						time_output += '<span class="extension-hotspot-minutes-to-go">' + Math.floor( Math.floor(clock.seconds_to_go % 3600)  / 60) + '</span>';
						if( clock.seconds_to_go <= 300 ){
							time_output += '<span class="extension-hotspot-seconds-to-go">' + Math.floor(clock.seconds_to_go % 60) + '</span>';
						}
						time_output += '<span class="extension-hotspot-to-go"> to go</span>';
						time_output += '</div>'

					}

					clone.querySelectorAll('.extension-hotspot-time' )[0].innerHTML = time_output;
				    */
					document.getElementById('extension-hotspot-list').append(clone);
				}); // end of looping over items
                
                this.sort_items("count");
			
                if(this.protected_animals_count != 0){
                    
                    //document.getElementById('extension-hotspot-protected-animals-count').innerText = this.protected_animals_count;
                    //document.getElementById('extension-hotspot-protected-animals-count-container').style.display = 'block';
                }
            
			}
			catch (e) {
				// statements to handle any exceptions
				//console.log(e); // pass exception object to error handler
			}
		}
        
        
        //
        //  sort items in various ways
        //
        
        sort_items(type){
            //console.log("in sort_items. Type = " + type);
            const sortChildren = ({ container, childSelector, getScore }) => {
              const items = [...container.querySelectorAll(childSelector)];

              items
                .sort((a, b) => getScore(b) - getScore(a))
                .forEach(item => container.appendChild(item));
            };
            
            if(type == 'count'){
                //console.log("sort type is count");
                
                document.querySelectorAll('.extension-hotspot-domains').forEach(function(node) {
                    //console.log(node);
                    sortChildren({
                      container: node,
                      childSelector: ".extension-hotspot-domain-item",
                      getScore: item => {
                        const rating = item.querySelector(".extension-hotspot-domain-count");
                        //console.log("rating element:")
                        //console.log(rating)
                        if (!rating) return 0;
                        //const scoreString = [...rating.classList].find(c => /r\d+/.test(c)); // based on classnames
                        //const scoreString = [...rating.innerText]; //.find(c => /r\d+/.test(c));
                        //console.log("scoreString = " + scoreString);
                        //const score = parseInt(scoreString.slice(1));
                        //const score = parseInt(scoreString);
                        //return score;
                        return parseInt(rating.innerText)
                      }
                    });
                });
                
                
                
            }

            
            
        }
        
        
        
        
        
	}

	new Hotspot();
	
})();


