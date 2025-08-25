{
  description = "K4fk4Gewinnt flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };
  outputs = { self, nixpkgs }: 
    let 
        pkgs = import nixpkgs { 
            system = "x86_64-linux"; 
            config.allowUnfree = true;
        };
        system = "x86_64-linux";
    in {
        devShells.x86_64-linux.default = pkgs.mkShell {
            buildInputs = [
                pkgs.docker
                pkgs.docker-compose
                pkgs.python312
                pkgs.python312Packages.requests
                pkgs.python312Packages.colorama
                pkgs.python312Packages.websocket-client
                pkgs.python312Packages.python-dotenv
            ];

            shellHook = ''
                alias up='docker-compose up --build -d'
                alias down='docker-compose down'
                clean() {
                docker-compose down --rmi local -v --remove-orphans
                docker rm -f $(docker ps -aq)
                docker volume rm $(docker volume ls -q)
                }
            '';
        };
    };
}
