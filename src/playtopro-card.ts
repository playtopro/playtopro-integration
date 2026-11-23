// src/playtopro-card.ts
//
// Release process
//
// Push a tag (git tag vYYYY.M.D && git push origin vYYYY.M.D). The release
// workflow builds this card into custom_components/playtopro/frontend/
// (the built file is not committed), writes the tag's version into
// manifest.json, const.py and package.json, and publishes playtopro.zip.
//
// Entities are matched by unique ID ("<serial>_<key>", see entity.py in the
// integration), so renaming them in Home Assistant doesn't break the card.

import { LitElement, html, css } from "lit";
import type { HassEntity } from "home-assistant-js-websocket";
import type { HomeAssistant, LovelaceCardConfig } from "custom-card-helpers";
//import type PlayToProCardEditor from "../editor/playtopro-card-editor"
import "./editor/playtopro-card-editor";

// ---------------- Types ----------------

export interface PlayToProCardConfig extends LovelaceCardConfig {
  device_id: string;
}

export interface GroupConfig {
  name: string;
  icon: string;
  /** Key of the device-wide switch for this group, if any. */
  device_key?: string;
  information?: string;
  /** Key of the per-zone switches, without the "_NN" zone suffix. */
  zone_key: string;
}

export interface PlayToProConfig {
  zone_key: string;
  zone_count: number;
  groups: GroupConfig[];
}

interface RegistryEntry {
  entity_id: string;
  device_id?: string | null;
  unique_id?: string;
  original_name?: string | null;
}

interface ShowNotificationEventDetail {
  message: string;
  duration?: number;
}

// ----------- Entity mapping (unique ID keys from the integration) ------------

const entityConfig: PlayToProConfig = {
  zone_key: "zone",
  zone_count: 8,
  groups: [
    {
      name: "Auto Mode",
      icon: "mdi:checkbox-marked-circle-auto-outline",
      device_key: "auto_mode",
      information:
        "Turn on to use the schedule set in the lichen play app, turn off to schedule using Home Assistant",
      zone_key: "zone_auto_mode",
    },
    {
      name: "Eco Mode",
      icon: "mdi:leaf",
      device_key: "eco_mode",
      information:
        "Turn on eco mode to save water during cooler and wet weather",
      zone_key: "zone_eco_mode",
    },
    {
      name: "Manual Mode",
      icon: "mdi:run",
      information:
        "Manual run allows you to directly control each zone, use these in your HA automation",
      zone_key: "zone_manual_mode",
    },
  ],
};

const zoneSuffix = (index: number) => `_${String(index).padStart(2, "0")}`;

// ---------------- Card (React-style class) ----------------

export class PlaytoproCard extends LitElement {
  // --- Styles ---
  static styles = css`
    ha-card {
      padding: 16px;
    }
    .entity {
      margin: 8px 0;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    ha-icon {
      color: var(--primary-color);
      margin-left: 8px;
      vertical-align: middle;
    }
    @keyframes pulse {
      0% {
        opacity: 1;
      }
      30% {
        opacity: 0.4;
      }
      50% {
        opacity: 1;
      }
      100% {
        opacity: 1;
      }
    }
    ha-icon.pulsing {
      animation: pulse 2.5s infinite;
    }
    ha-icon.off {
      color: var(--disabled-text-color);
      opacity: 0.6;
    }
    ha-control-select ha-icon {
      vertical-align: middle;
      color: var(--primary-color);
    }
  `;

  // --- HA-managed "props" ---
  private _hass?: HomeAssistant; // backing field for getter/setter
  private _config?: PlayToProCardConfig; // set via setConfig()

  // --- Your internal "state" ---
  private _selectedGroup: number;
  private _deviceId?: string;
  /** This device's entities, keyed by unique ID without the serial prefix. */
  private _deviceEntities: Map<string, RegistryEntry>;
  private _loadedDeviceId?: string;
  private _loading = false;

  constructor() {
    super();
    // Initialize state (React constructor style)
    this._selectedGroup = entityConfig.groups.length - 1;
    this._deviceEntities = new Map();
  }

  // React: componentDidMount
  connectedCallback() {
    super.connectedCallback();
    // Nothing special needed here yet (bootstrap happens in setConfig)
  }

  // React: componentWillUnmount
  disconnectedCallback() {
    super.disconnectedCallback();
    // Clean up timers/subscriptions if you add any later.
  }

  // Expose hass as a property HA writes to repeatedly (React-like "new props")
  public get hass() {
    return this._hass as HomeAssistant;
  }

  public set hass(next: HomeAssistant) {
    if (this._hass !== next) {
      this._hass = next;

      if (this._deviceId && this._deviceId !== this._loadedDeviceId) {
        this.loadEntities();
      }

      this.requestUpdate();
    }
  }

  // Lovelace calls this exactly once with the card configuration (React: "receive initial props")
  public setConfig(config: PlayToProCardConfig): void {
    this._config = config;
    this._deviceId = config.device_id;
    if (this._hass && this._deviceId && this._deviceId !== this._loadedDeviceId) {
      this.loadEntities();
    }
  }

  // Load this device's entities from the entity registry (once per device)
  private async loadEntities() {
    if (!this._hass || !this._deviceId || this._loading) return;
    const deviceId = this._deviceId;
    this._loading = true;

    try {
      const entities = await this._hass.callWS<RegistryEntry[]>({
        type: "config/entity_registry/list",
      });
      const byKey = new Map<string, RegistryEntry>();
      for (const e of entities) {
        if (e.device_id !== deviceId || !e.unique_id) continue;
        const separator = e.unique_id.indexOf("_");
        if (separator > 0) byKey.set(e.unique_id.slice(separator + 1), e);
      }
      this._deviceEntities = byKey;
      this._loadedDeviceId = deviceId;
    } catch (err) {
      console.warn("playtopro-card: unable to load entities", err);
    } finally {
      this._loading = false;
      this.requestUpdate();
    }
  }

  // React: shouldComponentUpdate
  protected shouldUpdate(_changed: Map<string, unknown>) {
    // Return false to skip renders if you need performance optimisations.
    return true;
  }

  // React: componentDidUpdate(prevProps, prevState)
  protected updated(_changed: Map<string, unknown>) {
    // Post-render effects if needed.
  }

  // --- UI event handlers ---

  private _groupChanged = (e: CustomEvent) => {
    const n = Number(e.detail.value);
    if (!Number.isNaN(n) && n !== this._selectedGroup) {
      this._selectedGroup = n;
      this.requestUpdate();
    }
  };

  private _entityClicked = (e: Event) => {
    const el = e.currentTarget as HTMLElement;
    const entityId = el.dataset.entityId;
    if (!entityId) return;

    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      })
    );
  };

  private _informationClicked = (e: Event) => {
    const el = e.currentTarget as HTMLElement;
    const information = el.dataset.information?.trim();
    if (!information) return;

    const evt = new CustomEvent<ShowNotificationEventDetail>(
      "hass-notification",
      {
        detail: { message: information, duration: 8000 },
        bubbles: true,
        composed: true,
      }
    );
    this.dispatchEvent(evt);
  };

  private _getIconForState(value: string): string {
    switch ((value ?? "").toLowerCase()) {
      case "on":
        return "mdi:sprinkler-variant";
      case "off":
        return "mdi:sprout";
      default:
        return "mdi:help-circle";
    }
  }

  private async _toggleEntity(e: Event) {
    const input = e.currentTarget as HTMLInputElement;
    const entityId = input.dataset.entityId;
    if (!entityId || !this._hass) return;

    await this._hass.callService(
      "switch",
      input.checked ? "turn_on" : "turn_off",
      {
        entity_id: entityId,
      }
    );
    // HA state update will come via hass setter; requestUpdate() is harmless here
    this.requestUpdate();
  }

  // --- render (React: render()) ---

  protected render() {
    if (!this._hass) {
      return html`<ha-card><div>Waiting for Home Assistant...</div></ha-card>`;
    }
    else if (!this._config) {
      return html`<ha-card><div>No configuration...</div></ha-card>`;
    }
    else if (this._config.device_id === undefined) {
      return html`<ha-card
        ><div>No device configured, check yaml...</div></ha-card
      >`;
    }
    else if (this._config.device_id === "") {
      return html`<ha-card><div>No device selected...</div></ha-card>`;
    }
    else if (this._deviceEntities.size === 0) {
      return html`<ha-card><div>Loading entities...</div></ha-card>`;
    }

    const groupCfg: GroupConfig = entityConfig.groups[this._selectedGroup];
    const groupEntity = groupCfg.device_key
      ? this._deviceEntities.get(groupCfg.device_key)
      : undefined;
    const groupEntityState: HassEntity | undefined = groupEntity
      ? this._hass.states[groupEntity.entity_id]
      : undefined;

    return html`
      <ha-card>
        <ha-control-select
          fixedMenuPosition
          naturalMenuWidth
          .value=${String(this._selectedGroup)}
          @value-changed=${this._groupChanged}
          .options=${entityConfig.groups.map((g, i) => ({
            value: String(i),
            icon: html`<ha-icon icon=${g.icon}></ha-icon>`,
          }))}
        >
        </ha-control-select>

        <div class="content">
          <div class="entity">
            <span>${groupCfg.name}</span>
            <div style="display:flex;align-items:center;">
              ${groupEntityState
                ? html`
                    <ha-switch
                      .checked=${groupEntityState?.state === "on"}
                      data-entity-id=${groupEntity?.entity_id ?? ""}
                      @change=${this._toggleEntity}
                    ></ha-switch>`
                : html``
              }
              ${groupCfg.information
                ? html `
                    <ha-icon
                      role="img"
                      aria-label="Information"
                      style="cursor:pointer"
                      icon="mdi:information"
                      data-information=${groupCfg.information ?? ""}
                      @click=${this._informationClicked}
                    ></ha-icon>`
                : html``
              }
            </div>
          </div>

          ${Array.from({ length: entityConfig.zone_count }, (_, index) => {
            const zoneEntity = this._deviceEntities.get(
              entityConfig.zone_key + zoneSuffix(index)
            );
            const groupZoneEntity = this._deviceEntities.get(
              groupCfg.zone_key + zoneSuffix(index)
            );
            if (!zoneEntity || !groupZoneEntity) return html``;

            const zone_original_name =
              zoneEntity.original_name ?? `Zone ${String(index + 1).padStart(2, "0")}`;
            const zoneState: HassEntity | undefined =
              this._hass!.states[zoneEntity.entity_id];
            const groupZoneEnitityState: HassEntity | undefined =
              this._hass!.states[groupZoneEntity.entity_id];

            if (!zoneState || !groupZoneEnitityState) return html``;

            return html`
              <div class="entity">
                <span
                  style="cursor:pointer"
                  @click=${this._entityClicked}
                  data-entity-id=${zoneEntity.entity_id}
                >
                  ${zoneState.attributes.friendly_name ?? zone_original_name}
                </span>
                <div style="display:flex;align-items:center;">
                  <ha-switch
                    .checked=${groupZoneEnitityState.state === "on"}
                    .disabled=${groupEntityState?.state === "off"}
                    data-entity-id=${groupZoneEntity.entity_id}
                    @change=${this._toggleEntity}
                  ></ha-switch>
                  <ha-icon
                    role="img"
                    aria-label="${zoneState.attributes.friendly_name ??
                    zone_original_name} is ${zoneState.state}"
                    icon=${this._getIconForState(zoneState.state)}
                  ></ha-icon>
                </div>
              </div>
            `;
          })}
        </div>
      </ha-card>
    `;
  }

  // Lovelace sizing hint
  public getCardSize(): number {
    return 2 + entityConfig.zone_count;
  }

  // Lovelace editor factory
  public static getConfigElement(): HTMLElement {
    return document.createElement("playtopro-card-editor");
  }


  public static getStubConfig(): { device_id: string } {
    // IMPORTANT: no "type" here
    return { device_id: "" };
  }

}

// Register the element
customElements.define("playtopro-card", PlaytoproCard);

// Optional: register metadata for the card picker
declare global {
  interface HTMLElementTagNameMap {
    "playtopro-card": PlaytoproCard;
  }
  interface Window {
    customCards?: Array<{ type: string; name: string; description: string }>;
  }
}
window.customCards = window.customCards || [];
window.customCards.push({
  type: "playtopro-card",
  name: "playtopro card",
  description: "Organize and control lichen play devices.",
});
