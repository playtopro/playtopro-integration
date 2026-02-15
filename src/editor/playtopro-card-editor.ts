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

  setConfig(config: PlayToProCardConfig): void {
    this._config = config;
  }

  private _deviceFilter = (device: DeviceRegistryEntry): boolean =>
    device.model === "lichen play";

  render() {
    if (!this._config) return nothing;

    return html`
      <div class="card-config">
        <ha-device-picker
          .hass=${this._hass}
          .value=${this._config.device_id}
          .deviceFilter=${this._deviceFilter}
          @value-changed=${this._deviceChanged}
        ></ha-device-picker>
      </div>
    `;
  }

  private _deviceChanged = (ev: CustomEvent<{ value: string }>) => {
    const deviceId = ev.detail.value;
    this._config = { ...this._config!, device_id: deviceId };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
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
