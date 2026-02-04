// src/playtopro-card.ts
// A React-style (class + constructor + explicit state) custom Lovelace card.
// No decorators, no Babel needed. Bundles to a single ES module for HACS.

import { LitElement, html, css } from "lit";
import type { HassEntity } from "home-assistant-js-websocket";
import type { HomeAssistant, LovelaceCardConfig } from "custom-card-helpers";
import "./editor/playtopro-card-editor";

// ---------------- Types ----------------

export interface PlayToProCardConfig extends LovelaceCardConfig {
  device_id: string;
}

export interface GroupConfig {
  name: string;
  icon: string;
  entity_id?: string;
  information?: string;
  entities: string[];
}

export interface PlayToProConfig {
  eco_mode_factor: string;
  eco_mode: string;
  zones: string[];
  groups: GroupConfig[];
}

interface ShowNotificationEventDetail {
  message: string;
  duration?: number;
}

// ----------- Hard-coded entity mapping (adjust later if desired) ------------

const entityConfig: PlayToProConfig = {
  eco_mode_factor: "sensor.eco_mode_factor",
  eco_mode: "switch.eco_mode",
  zones: [
    "sensor.zone_01",
    "sensor.zone_02",
    "sensor.zone_03",
    "sensor.zone_04",
    "sensor.zone_05",
    "sensor.zone_06",
    "sensor.zone_07",
    "sensor.zone_08",
  ],
  groups: [
    {
      name: "Auto Mode",
      icon: "mdi:checkbox-marked-circle-auto-outline",
      entity_id: "switch.auto_mode",
      information:
        "Turn on to use the schedule set in the lichen play app, turn off to schedule using Home Assistant",
      entities: [
        "switch.zone_01_auto_mode",
        "switch.zone_02_auto_mode",
        "switch.zone_03_auto_mode",
        "switch.zone_04_auto_mode",
        "switch.zone_05_auto_mode",
        "switch.zone_06_auto_mode",
        "switch.zone_07_auto_mode",
        "switch.zone_08_auto_mode",
      ],
    },
    {
      name: "Eco Mode",
      icon: "mdi:leaf",
      entity_id: "switch.eco_mode",
      information: "Turn on eco mode to save water during cooler and wet weather",
      entities: [
        "switch.zone_01_eco_mode",
        "switch.zone_02_eco_mode",
        "switch.zone_03_eco_mode",
        "switch.zone_04_eco_mode",
        "switch.zone_05_eco_mode",
        "switch.zone_06_eco_mode",
        "switch.zone_07_eco_mode",
        "switch.zone_08_eco_mode",
      ],
    },
    {
      name: "Sleep Mode",
      icon: "mdi:sleep",
      entities: [
        "switch.zone_01_sleep_mode",
        "switch.zone_02_sleep_mode",
        "switch.zone_03_sleep_mode",
        "switch.zone_04_sleep_mode",
        "switch.zone_05_sleep_mode",
        "switch.zone_06_sleep_mode",
        "switch.zone_07_sleep_mode",
        "switch.zone_08_sleep_mode",
      ],
    },
    {
      name: "Manual Mode",
      icon: "mdi:run",
      entities: [
        "switch.zone_01_manual_mode",
        "switch.zone_02_manual_mode",
        "switch.zone_03_manual_mode",
        "switch.zone_04_manual_mode",
        "switch.zone_05_manual_mode",
        "switch.zone_06_manual_mode",
        "switch.zone_07_manual_mode",
        "switch.zone_08_manual_mode",
      ],
    },
  ],
};

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
      0% { opacity: 1; }
      30% { opacity: 0.4; }
      50% { opacity: 1; }
      100% { opacity: 1; }
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
  private _hass?: HomeAssistant;           // backing field for getter/setter
  private _config?: PlayToProCardConfig;   // set via setConfig()

  // --- Your internal "state" ---
  private _selectedGroup: number;
  private _deviceId?: string;
  private _deviceEntities: Array<{ entity_id: string; [k: string]: unknown }>;

  constructor() {
    super();
    // Initialize state (React constructor style)
    this._selectedGroup = 0;
    this._deviceEntities = [];
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

        if (this._deviceId && this._deviceEntities.length === 0) {
            this.loadEntities();
        }

        this.requestUpdate();
    }
}

  // Lovelace calls this exactly once with the card configuration (React: "receive initial props")
  public setConfig(config: PlayToProCardConfig): void {
    console.log("setConfig called");
    if (config.device_id === undefined) throw new Error("device_id is required");
    this._config = config;
    this._deviceId = config.device_id;
  }

  // Async initializer for device + entities
  private async loadEntities() {
    if (!this._hass || !this._deviceId) return;

    try {
      const entities = await this._hass.callWS<any[]>({ type: "config/entity_registry/list" });
      this._deviceEntities = entities.filter((e) => e.device_id === this._deviceId);
    } catch {
    } finally { 
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

    const evt = new CustomEvent<ShowNotificationEventDetail>("hass-notification", {
      detail: { message: information, duration: 8000 },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(evt);
  };

  private _getIconForState(value: string): string {
    switch ((value ?? "").toLowerCase()) {
      case "true":
        return "mdi:sprinkler-variant";
      case "false":
        return "mdi:sprout";
      default:
        return "mdi:help-circle";
    }
  }

  private async _toggleEntity(e: Event) {
    const input = e.currentTarget as HTMLInputElement;
    const entityId = input.dataset.entityId;
    if (!entityId || !this._hass) return;

    await this._hass.callService("switch", input.checked ? "turn_on" : "turn_off", {
      entity_id: entityId,
    });
    // HA state update will come via hass setter; requestUpdate() is harmless here
    this.requestUpdate();
  }

  // --- render (React: render()) ---

  protected render() {

    if (this._deviceEntities.length === 0) {
      return html`<ha-card><div>Loading entities…</div></ha-card>`;
    }
    if (!this._hass || !this._config) {
      return html`<ha-card><div>Waiting for Home Assistant…</div></ha-card>`;
    }
    if (this._config.device_id === undefined) {
      return html`<ha-card><div>No device configured, check yaml...</div></ha-card>`;
    }
    if (this._config.device_id === "") {
      return html`<ha-card><div>No device selected...</div></ha-card>`;
    }

    const groupCfg: GroupConfig = entityConfig.groups[this._selectedGroup];
    const groupEntityState: HassEntity | undefined = groupCfg.entity_id
      ? this._hass.states[groupCfg.entity_id]
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
                      .checked=${groupEntityState.state === "on"}
                      data-entity-id=${groupCfg.entity_id ?? ""}
                      @change=${this._toggleEntity}
                    ></ha-switch>
                    <ha-icon
                      role="img"
                      aria-label="Information"
                      style="cursor:pointer"
                      icon="mdi:information"
                      data-information=${groupCfg.information ?? ""}
                      @click=${this._informationClicked}
                    ></ha-icon>
                  `
                : html``}
            </div>
          </div>

          ${entityConfig.zones.map((zoneId, index) => {
            // Only show zone rows for entities that belong to this device
            const zoneEntry = this._deviceEntities.find((e) => e.entity_id === zoneId);
            if (!zoneEntry) return html``;

            const zoneState: HassEntity | undefined = this._hass!.states[zoneId];
            const groupZoneId = entityConfig.groups[this._selectedGroup].entities[index];
            const groupZoneState: HassEntity | undefined = groupZoneId
              ? this._hass!.states[groupZoneId]
              : undefined;

            if (!zoneState || !groupZoneId || !groupZoneState) return html``;

            return html`
              <div class="entity">
                <span
                  style="cursor:pointer"
                  @click=${this._entityClicked}
                  data-entity-id=${zoneId}
                >
                  ${zoneState.attributes.friendly_name ?? zoneId}
                </span>
                <div style="display:flex;align-items:center;">
                  <ha-switch
                    .checked=${groupZoneState.state === "on"}
                    .disabled=${groupEntityState?.state === "off"}
                    data-entity-id=${groupZoneId}
                    @change=${this._toggleEntity}
                  ></ha-switch>
                  <ha-icon
                    role="img"
                    aria-label="${(zoneState.attributes.friendly_name ?? zoneId)} is ${zoneState.state}"
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
    return 2 + entityConfig.zones.length;
  }

  // Lovelace editor factory
  static async getConfigElement() {
    return document.createElement("playtopro-card-editor");
  }

  // Card picker stub
  public static getStubConfig(): PlayToProCardConfig {
    return { type: "custom:playtopro-card", device_id: "" };
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
  name: "Playtopro Card",
  description: "Organize and control lichen play zones.",
});