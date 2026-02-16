
// src/playtopro-card.ts
//
// Release process (IMPORTANT: order matters)
//
// To create a new release:
//
// 1. Update version in custom_components/playtopro/manifest.json
//    - This is the version HACS and Home Assistant use.
//
// 2. Update version in package.json
//    - Used for local/npm tooling only (not required by HACS, but recommended).
//
// 3. Update version in custom_components/playtopro/const.ts
//    - Used for display (e.g. card picker, logging). Optional but recommended.
//
// 4. Run the build to update the bundled frontend JS:
//      npm run build
//    - This must update:
//      custom_components/playtopro/frontend/playtopro-card.js
//
// 5. Commit and push ALL changes (including the built JS):
//      git add .
//      git commit -m "Release vYYYY.M.X"
//      git push
//
// 6. Create and push a Git tag that points to THIS commit:
//      git tag vYYYY.M.X
//      git push origin vYYYY.M.X
//
// 7. The GitHub Actions release workflow will run automatically:
//    - It creates the GitHub Release from the tag
//    - The tagged source already contains the correct built JS
//    - No build happens in CI (source and release stay consistent)
//
// ⚠️ Do NOT rebuild or modify files after tagging.
//    Tags must always point to the exact code that is released.

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
  entity_original_name?: string;
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
    "Zone 01",
    "Zone 02",
    "Zone 03",
    "Zone 04",
    "Zone 05",
    "Zone 06",
    "Zone 07",
    "Zone 08",
  ],
  groups: [
    {
      name: "Auto Mode",
      icon: "mdi:checkbox-marked-circle-auto-outline",
      entity_original_name: "Auto Mode",
      information:
        "Turn on to use the schedule set in the lichen play app, turn off to schedule using Home Assistant",
      entities: [
        "Zone 01 Auto Mode",
        "Zone 02 Auto Mode",
        "Zone 03 Auto Mode",
        "Zone 04 Auto Mode",
        "Zone 05 Auto Mode",
        "Zone 06 Auto Mode",
        "Zone 07 Auto Mode",
        "Zone 08 Auto Mode",
      ],
    },
    {
      name: "Eco Mode",
      icon: "mdi:leaf",
      entity_original_name: "Eco Mode",
      information:
        "Turn on eco mode to save water during cooler and wet weather",
      entities: [
        "Zone 01 Eco Mode",
        "Zone 02 Eco Mode",
        "Zone 03 Eco Mode",
        "Zone 04 Eco Mode",
        "Zone 05 Eco Mode",
        "Zone 06 Eco Mode",
        "Zone 07 Eco Mode",
        "Zone 08 Eco Mode",
      ],
    },
    //{
    //  name: "Sleep Mode",
    //  icon: "mdi:sleep",
    //  entities: [
    //    "Zone 01 Sleep Mode",
    //    "Zone 02 Sleep Mode",
    //    "Zone 03 Sleep Mode",
    //    "Zone 04 Sleep Mode",
    //    "Zone 05 Sleep Mode",
    //    "Zone 06 Sleep Mode",
    //    "Zone 07 Sleep Mode",
    //    "Zone 08 Sleep Mode",
    //  ],
    //},
    {
      name: "Manual Mode",
      icon: "mdi:run",
      information:
        "Manual run allows you to directly control each zone, use these in your HA automation",
      entities: [
        "Zone 01 Manual Mode",
        "Zone 02 Manual Mode",
        "Zone 03 Manual Mode",
        "Zone 04 Manual Mode",
        "Zone 05 Manual Mode",
        "Zone 06 Manual Mode",
        "Zone 07 Manual Mode",
        "Zone 08 Manual Mode",
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
  private _deviceEntities: Array<{ entity_id: string; [k: string]: unknown }>;

  constructor() {
    super();
    // Initialize state (React constructor style)
    this._selectedGroup = entityConfig.groups.length - 1;
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
    //if (config.device_id && config.device_id !== "")
    //{
      this._config = config;
      this._deviceId = config.device_id;
    //}
  }

  // Async initializer for device + entities
  private async loadEntities() {
    if (!this._hass || !this._deviceId) return;

    try {
      const entities = await this._hass.callWS<any[]>({
        type: "config/entity_registry/list",
      });
      this._deviceEntities = entities.filter(
        (e) => e.device_id === this._deviceId
      );
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
    else if (this._deviceEntities.length === 0) {
      return html`<ha-card><div>Loading entities...</div></ha-card>`;
    }

    let groupCfg: GroupConfig = entityConfig.groups[this._selectedGroup];
    let groupEntity = groupCfg.entity_original_name ? this._deviceEntities.find(
      (e) => e.original_name === groupCfg.entity_original_name
    ) : undefined;
    let groupEntityState: HassEntity | undefined = groupEntity
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

          ${entityConfig.zones.map((zone_original_name, index) => {
            // Only show zone rows for entities that belong to this device
            const zoneEntity = this._deviceEntities.find(
              (e) => e.original_name === zone_original_name
            );
            if (!zoneEntity) return html``;

            const zoneState: HassEntity | undefined =
              this._hass!.states[zoneEntity.entity_id];
            const groupZoneEntityOriginalName = groupCfg.entities[index];
            const groupZoneEntity = this._deviceEntities.find(
              (e) => e.original_name === groupZoneEntityOriginalName
            );

            if (!groupZoneEntity) return html``;

            const groupZoneEnitityState: HassEntity | undefined = groupZoneEntity
              ? this._hass!.states[groupZoneEntity.entity_id]
              : undefined;

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
    return 2 + entityConfig.zones.length;
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
