import { LitElement, html, nothing, css } from "lit";
import type { HomeAssistant, LovelaceCardEditor } from "custom-card-helpers";
import type { PlayToProCardConfig } from "../playtopro-card";

// Minimal device type for filtering (no internal HA types needed)
type DeviceRegistryEntry = {
  id: string;
  model?: string;
  name?: string;
  manufacturer?: string;
};

export class PlayToProCardEditor
  extends LitElement
  implements LovelaceCardEditor
{


  // --- HA-managed "props" ---
  private _hass?: HomeAssistant; // backing field for getter/setter
  private _config?: PlayToProCardConfig; // set via setConfig()

  set hass(hass: HomeAssistant) {
    this._hass = hass;
    this.requestUpdate();
  }

  setConfig(config: PlayToProCardConfig): void {
    this._config = config;
    this.requestUpdate();
  }

  render() {
    if (!this._config) return nothing;

    return html`
      <div class="card-config">
        <ha-selector
            .hass=${this._hass}
            .value=${this._config.device_id}
            .selector=${{
                device: {
                filter: { model: "lichen play" }
                }
            }}
            @value-changed=${this._onDeviceChanged}
        ></ha-selector>
      </div>
    `;
  }

  private _onDeviceChanged = (ev: CustomEvent<{ value: string }>) => {
    const deviceId = ev.detail.value;
    this._config = { ...this._config!, device_id: deviceId };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  };
}

// Explicit registration (no @customElement)
customElements.define("playtopro-card-editor", PlayToProCardEditor);

declare global {
  interface HTMLElementTagNameMap {
    "playtopro-card-editor": PlayToProCardEditor;
  }
}
