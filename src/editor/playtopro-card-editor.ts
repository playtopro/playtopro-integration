import { LitElement, html, nothing, css } from "lit";
import type { HomeAssistant, LovelaceCardEditor } from "custom-card-helpers";
import type { PlayToProCardConfig } from "../playtopro-card";

// Minimal device type for filtering (no internal HA types needed)
type DeviceRegistryEntryLite = {
  id: string;
  model?: string;
  name?: string;
  manufacturer?: string;
};

export class PlayToProCardEditor
  extends LitElement
  implements LovelaceCardEditor
{
  // React-style: explicit fields + Lit reactive property table
  static properties = {
    hass:   { attribute: false },
    config: { attribute: false },
  };

  public hass!: HomeAssistant;
  public config?: PlayToProCardConfig;
  private _pickerReady = false;

  static styles = css`
    .card-config {
      display: grid;
      gap: 12px;
      padding: 8px 0;
    }
  `;

  /** HA calls this (may be slightly after first render). Be tolerant. */
  public setConfig(config: PlayToProCardConfig): void {
    this.config = config ?? { type: "playtopro-card", device_id: "" };
    this.requestUpdate();
  }

  // Only show devices whose model matches your controller
  private _deviceFilter = (device: DeviceRegistryEntryLite): boolean =>
    (device?.model ?? "").toLowerCase() === "lichen play"

  protected render() {
    // First render can happen before setConfig() → show a tiny placeholder
    if (!this.config) {
      return html`<div class="card-config"><p>Loading editor…</p></div>`;
    }

    return html`
      <div class="card-config">
        <ha-selector
            .hass=${this.hass}
            .value=${this.config.device_id}
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

  private _onDeviceChanged = (ev: CustomEvent<{ value?: string }>) => {
    const device_id = ev.detail?.value ?? "";
    this.config = { ...(this.config ?? { type: "playtopro-card" }), device_id };
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this.config } }));
  };
}

// Explicit registration (no @customElement)
customElements.define("playtopro-card-editor", PlayToProCardEditor);

declare global {
  interface HTMLElementTagNameMap {
    "playtopro-card-editor": PlayToProCardEditor;
  }
}