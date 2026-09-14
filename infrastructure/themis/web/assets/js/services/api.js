'use strict';

/******************************************************************************
 * Constants
 ******************************************************************************/

// Relative so the page works wherever nginx mounts it (currently /sophy/)
const API_BASE_URL = 'api/';

/******************************************************************************
 * API Functions
 ******************************************************************************/

const request_json = async (path, options = {}) => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    ...options,
  });

  let body = {};
  try {
    body = await response.json();
  } catch (error) {
    // A non-JSON body (nginx 401/502 page) is reported through the status below
  }

  if (!response.ok) {
    throw new Error(body.error || `${response.status} ${response.statusText}`);
  }
  return body;
};

// -> { devices: [{ number, description, configuration, mode }], modes: [...] }
const get_state = () => request_json('state');

// number is a device number or "all"; resolves to the new state
const switch_mode = (number, mode) => request_json('switch', {
  method: 'POST',
  body: JSON.stringify({ number, mode }),
});

export { get_state, switch_mode };
