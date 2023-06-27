{
  description = "A very basic flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-22.11";
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { nixpkgs, utils, ... }@inputs:

    utils.lib.eachSystem [ "x86_64-linux" "x86_64-darwin" ] (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python310.withPackages (p: [
          p.black
          p.mypy
          p.requests
          p.types-requests
        ]);
      in
      {
        devShells.default = pkgs.mkShell
          {
            packages = [ python ];
          };
      }
    );
}
