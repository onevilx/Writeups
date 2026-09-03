window.onload = async () => {
    statusConfig = await fetchServices();
    populateConfig(statusConfig);
    url = new URL(document.location.href);
    msg = url.searchParams.get("msg");
    archive = url.searchParams.get("export");
    if (msg) {
        showToast(msg, false);
    }
    $('#saveSettings').on('click', saveSettings);
    $('#checkSettings').on('click', checkSettings);
    $('#status-service').on('change', ()=> {
        service = statusConfig.filter(i => i.service == $('#status-service').val());
        if (!service.length) return;
        $('#status-url').val(service[0].host);
        $('#status-headers').val(service[0].headers);
        $('#status-state').val(service[0].status);
    })
}

const fetchServices = async () => {
    services = await fetch('/api/service/list')
    .then((response) => response.json()
        .then((data) => {
            return data;
        }))
    .catch((error) => {
        showToast(error.message);
    });
    return services;
};

const saveSettings = async () => {

	let host = $("#status-url").val();
	let headers = $("#status-headers").val();
    let service = $('#status-service').val();
    let status = $('#status-state').val();
	if ($.trim(host) === '') {
		showToast("Please input service URL first!");
		return;
	}

	await fetch(`/api/service/save`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({host, headers, service, status}),
		})
		.then((response) => response.json()
			.then((resp) => {
				showToast(resp.message);
			}))
		.catch((error) => {
			showToast(error.message);
		});

}

const checkSettings = async () => {

	let host = $("#status-url").val();
	let headers = $("#status-headers").val();
	if ($.trim(host) === '') {
		showToast("Please input service URL first!");
		return;
	}

    let parsedHeaders = {};
    try {
        let headersArray = headers.split('\n');
        for(let header of headersArray) {
            if(header.includes(':')) {
                let hkey = header.split(':')[0].trim()
                let hval = header.split(':')[1].trim()
                parsedHeaders[hkey] = hval;
            }
        }
    }
    catch (e) { console.log(e) }

	await fetch(`/api/service/check`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({host, headers: parsedHeaders}),
		})
		.then((response) => response.json()
			.then((resp) => {
				showToast(resp.message);
			}))
		.catch((error) => {
			showToast(error.message);
		});

}

const populateConfig = async (statusConfig) => {
    firstService = statusConfig[0];

    $('#status-url').val(firstService.host);
    $('#status-headers').val(firstService.headers);
    $('#status-state').val(firstService.status);

};

const showToast = (msg, fixed=false) => {
    $('#globalToast').hide();
    $('#globalToast').slideDown();
    $('#globalToastMsg').text(msg);
    if (!fixed) {
        setTimeout(() => {
            $('#globalToast').slideUp();
        }, 2500);
    }
}