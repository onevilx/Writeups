(($) => {
	var _base_serializeArray = $.fn.serializeArray;
	$.fn.serializeArray = function() {
		var a = _base_serializeArray.apply(this);
		$.each(this.find("input"), (i, e) => {
			if (e.type == "checkbox") {
				e.checked ?
					a[i].value = "true" :
					a.splice(i, 0, {
						name: e.name,
						value: "false"
					})
			}
		});
		return a;
	};
})(jQuery);

$(document).ready(() => {
	$("#saveSettingsBtn").on('click', saveSettings);
	$("#restoreSettingsBtn").on('click', restoreSettings);
	$("#buildStubBtn").on('click', buildStub);
	restoreSettings();
});

const getSettings = ($form) => {
	var unindexed_array = $form.serializeArray();
	var indexed_array = {};
	$.map(unindexed_array, (n, i) => {
		indexed_array[n['name']] = n['value'];
	});
	return indexed_array;
}

const mergeSettings = (target, source) => {
	for (let key in source) {
		if ((typeof target[key] === 'object') && (typeof source[key] === 'object')) {
			mergeSettings(target[key], source[key]);
		} else {
			target[key] = source[key];
		}
	}
	return target;
}

const hideToast = () => {
	$("#resp-msg-text").text('');
	$("#resp-msg").hide();
}

const restoreSettings = () => {
	$.get('/api/settings', (savedSettings) => {
		if (typeof savedSettings === 'object') {
			defaultSettings = getSettings($('#builder-form'));
			userSettings = mergeSettings(defaultSettings, savedSettings);
			Object.keys(userSettings).forEach((key) => {
				settingVal = userSettings[key];
				if (settingVal == "true" || settingVal == "false") {
					$(`[name=${key}]`).prop("checked", (settingVal == "true") ? true : false);
				} else {
					$(`[name=${key}]`).val(settingVal);
				}
			})
			$("#resp-msg-text").text("Settings restored!");
			$("#resp-msg").show();
			setTimeout(() => {
				$("#resp-msg").hide()
			}, 1000);
		}
	});
}

const saveSettings = () => {
	userSettings = getSettings($('#builder-form'));
	$.ajax({
		url: '/api/settings',
		type: 'post',
		dataType: 'json',
		contentType: 'application/json',
		data: JSON.stringify(userSettings),
		success: (data) => {
			if (data.message) {
				$("#resp-msg-text").text(data.message);
			} else {
				$("#resp-msg-text").text(data.toString());
			}
			$("#resp-msg").show();
			setTimeout(() => {
				$("#resp-msg").hide()
			}, 1000);
		},
		error: (request, status, error) => {
			try {
				response = JSON.parse(request.responseText).message;
			} catch {
				response = request.responseText;
			}
			$("#resp-msg-text").text(response);
			$("#resp-msg").show();
			setTimeout(() => {
				$("#resp-msg").hide()
			}, 1000);
		}
	});
}

const buildStub = () => {
	$('#buildStubBtn').prop('disabled', true);
	$.ajax({
		url: '/api/stub/build',
		type: 'get',
		success: (data) => {
			if (data.message) {
				$("#resp-msg-text").text(data.message);
			} else {
				$("#resp-msg-text").text(data.toString());
			}
			$("#resp-msg").show();
			setTimeout(() => {
				$("#resp-msg").hide()
			}, 1000);
			$('#buildStubBtn').prop('disabled', false);
		},
		error: (request, status, error) => {
			try {
				response = JSON.parse(request.responseText).message;
			} catch {
				response = request.responseText;
			}
			$("#resp-msg-text").text(response);
			$("#resp-msg").show();
			setTimeout(() => {
				$("#resp-msg").hide()
			}, 1000);
			$('#buildStubBtn').prop('disabled', false);
		}
	});
}

