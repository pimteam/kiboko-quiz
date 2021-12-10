KibokoQuiz = {'current_question' : 1}

KibokoQuiz.viewResults = function(e) {
	var answer_ids = [];
	jQuery('#quiz-' + this.exam_id + ' .answer-ids').each(function(index, value){
		answer_ids.push(this.value);
	});
	
	// if text captcha is there we have to make sure it's shown
	if(jQuery('#TextCaptcha').length && !jQuery('#TextCaptcha').is(':visible')) {
		alert("Please answer the verification question");
		jQuery('#TextCaptcha').show();
		return false;
	}
 
	var data = {'action': 'show_exam_result', quiz_id: exam_id, 
	'question_ids': KibokoQuiz.qArr, 'answer_ids' : answer_ids };
	
	if(jQuery('#watuTakerEmail').length) {
		var emailVal = jQuery('#watuTakerEmail').val();
		if(emailVal == '' || emailVal.indexOf('@') < 0 || emailVal.indexOf('.') < 1) {
			alert(watu_i18n.email_required);
			jQuery('#watuTakerEmail').focus();
			return false;
		} 
		data['taker_email'] = emailVal;
	}
	
	for(x=0; x<KibokoQuiz.qArr.length; x++) {
		if(KibokoQuiz.singlePage) {
			 KibokoQuiz.current_question = x+1;
			 
			 if(!KibokoQuiz.isAnswered() && KibokoQuiz.isRequired()) {
			 		alert("You have missed to answer a required question");
			 		return false;
			 }
		}		
		
    // qArr[x] is the question ID
		var ansgroup = '.answerof-'+KibokoQuiz.qArr[x];
		var fieldName = 'answer_'+KibokoQuiz.qArr[x];
		var ansvalues= Array();
		var i=0;
        
	    if(jQuery('#textarea_q_'+KibokoQuiz.qArr[x]).length>0) {
	        // open end question
	        ansvalues[0]=jQuery('#textarea_q_'+KibokoQuiz.qArr[x]).val();
	    } 
	    else {
	        jQuery(ansgroup).each(function(){
						if( jQuery(this).is(':checked') ) {
							ansvalues[i] = this.value;
							i++;
	  			}
	  		});    
	    }
		
		data[fieldName] = ansvalues;
	}
	//console.log(e);
	// no ajax? In this case only return true to allow submitting the form	
	if(e && e.no_ajax && e.no_ajax.value == 1) return true;	
	
	// if question captcha is available, add to data
	if(jQuery('#TextCaptcha').length>0) {
		jQuery('#quiz-'+KibokoQuiz.exam_id).show();
		data['text_captcha_answer'] = jQuery('#quiz-' + KibokoQuiz.exam_id + ' input[name=text_captcha_answer]').val();
		data['text_captcha_question'] = jQuery('#quiz-' + KibokoQuiz.exam_id + ' input[name=text_captcha_question]').val();
	}
	
	
	// change text and disable submit button
	jQuery("#action-button").val("Please wait...");
	jQuery("#action-button").attr("disabled", true);	
	
	// don't do ajax call if no_ajax
	if(!e || !e.no_ajax || e.no_ajax.value != 1) {		
		try{
			// hide quiz, display loading
			jQuery('#kiboko_quiz').hide();
			jQuery('#loading-result').show();
			jQuery.ajax({ type: 'POST', url: KibokoQuiz.ajax_url, data: data, success: KibokoQuiz.success, error: KibokoQuiz.error  });
		} catch(e) { alert(e) }
	}
} // end viewResults

KibokoQuiz.isAnswered = function() {
	if(jQuery('#questionType' + KibokoQuiz.current_question).val() == 'textarea') {
		if(jQuery('.textarea-'+KibokoQuiz.current_question).val()!='') return true;
		else return false;
	}
	
	var answered = false;
	
	jQuery("#question-" + KibokoQuiz.current_question + " .answer").each(function(i) {
			if(this.checked) {
				answered = true;
				return true;
			}
	});
	
	return answered;	
}

KibokoQuiz.isRequired = function() {
	if(jQuery('#questionType'+ KibokoQuiz.current_question).attr('class') == 'required') return true;
	
	return false;
}

KibokoQuiz.success = function(r){
	
	// first check for recaptcha error, if yes, do not replace the HTML
	 // but display the error in alert and return false;
	 if(r.indexOf('CAPTCHA:::')>-1) {
	 		parts = r.split(":::");
	 		alert(parts[1]);
	 		jQuery("#action-button").val("Try again");
			jQuery("#action-button").removeAttr("disabled");
			jQuery('#kiboko_quiz').show();
			jQuery('#loading-result').hide();
	 		return false;
	 } 

	 // redirect?
	 if(r.indexOf('REDIRECT:::') > -1) {
	 		parts = r.split(":::");
	 		window.location = parts[1];
	 		return true;
	 }
	
	jQuery('#loading-result').html(r);

	jQuery('#loading-result').show();	
}

KibokoQuiz.error = function(){ jQuery('#watu_quiz').html('Error Occured');}