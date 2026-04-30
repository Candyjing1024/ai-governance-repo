import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { environment } from '../../environment';

@Component({
  selector: 'app-settings',
  imports: [FormsModule],
  templateUrl: './settings.html'
})
export class Settings {
  endpoints = { ...environment };
  saved = false;

  save(): void {
    // Update the runtime environment object (persists for current session)
    Object.assign(environment, this.endpoints);
    this.saved = true;
    setTimeout(() => this.saved = false, 3000);
  }

  reset(): void {
    this.endpoints = {
      projectsApi: 'http://localhost:5218',
      modelsApi: 'http://localhost:5076',
      agentsApi: 'http://localhost:5300',
      gatewayApi: 'http://localhost:5099',
      usersApi: 'http://localhost:5145',
    };
  }
}
